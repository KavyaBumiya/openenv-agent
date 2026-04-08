"""
Rule-based grader: Fast, deterministic, reproducible.

This is the PRIMARY grader for agent training.
Use this for:
- Training runs (fast, no API calls)
- Offline evaluation
- Debugging agent behavior
- Consistent across machines

Do NOT use for:
- Human review (use AIEnhancedGrader instead)
"""

import logging
from typing import Dict, Any
from pydantic import BaseModel
from .semantic_evaluator import get_semantic_evaluator

logger = logging.getLogger(__name__)

# EPSILON for strict bounds: scores must be strictly > 0 and strictly < 1
_STRICT_SCORE_EPSILON = 0.001


def _term_variants(term: str) -> set[str]:
    """Generate normalized variants of a term for keyword matching.
    
    Handles English inflections including silent-e rule:
    - resolve + ed → resolved (drop silent-e)
    - route + ing → routing (drop silent-e)
    - help + ed → helped (simple addition)
    """
    normalized = term.lower().strip()
    variants = {normalized}
    
    # First pass: try stripping each suffix to find base forms
    for suffix in ("ed", "ing", "s", "tion"):
        if len(normalized) > len(suffix) + 2 and normalized.endswith(suffix):
            base = normalized[: -len(suffix)]
            variants.add(base)
            # For the base form, also try adding other suffixes
            for other_suffix in ("ed", "ing", "s"):
                if other_suffix != suffix and len(base + other_suffix) < 30:
                    variants.add(base + other_suffix)
    
    # Second pass: for the original word, if it's already a base form (no suffix),
    # also add common inflections (handling silent-e rule)
    is_base = not any(
        normalized.endswith(suf) and len(normalized) > len(suf) + 2
        for suf in ("ed", "ing", "s", "tion")
    )
    
    if is_base:
        # For "ing": drop trailing 'e' before adding 'ing'
        if normalized.endswith("e") and len(normalized) > 3:
            variants.add(normalized[:-1] + "ing")  # resolve → resolving
        variants.add(normalized + "ing")  # help → helping
        
        # For "ed": drop trailing 'e' before adding 'ed'
        if normalized.endswith("e") and len(normalized) > 3:
            variants.add(normalized[:-1] + "ed")  # resolve → resolved
        variants.add(normalized + "ed")  # help → helped
        
        # For "s": just add it (usually works)
        variants.add(normalized + "s")  # help → helps
    
    return {v for v in variants if v and len(v) > 2}


def _strict_unit_score(value: float) -> float:
    """Clamp a score to the open interval (0, 1) — never exactly 0.0 or 1.0.
    
    Prevents rounding from producing exact boundaries.
    """
    clamped = min(1.0 - _STRICT_SCORE_EPSILON, max(_STRICT_SCORE_EPSILON, float(value)))
    result = round(clamped, 4)
    # Guard against float rounding producing exact boundary
    if result <= 0.0:
        return _STRICT_SCORE_EPSILON
    if result >= 1.0:
        return 1.0 - _STRICT_SCORE_EPSILON
    return result


class ScoreComponent(BaseModel):
    """Fine-grained score for a single component."""
    value: float  # Strictly in (0, 1)
    weight: float  # How much this component contributes to overall score
    reasoning: str  # Why this score was awarded
    max_possible: float = 1.0  # For debugging


class DetailedScoreBreakdown(BaseModel):
    """Transparent breakdown of grading decision for agent learning."""
    
    # Component scores
    category_score: ScoreComponent
    priority_score: ScoreComponent
    department_score: ScoreComponent | None = None
    escalation_score: ScoreComponent | None = None
    response_score: ScoreComponent | None = None
    
    # Penalties and bonuses
    enterprise_penalty: float = 0.0  # Amount deducted for enterprise + wrong priority
    sla_penalty: float = 0.0  # Amount deducted for SLA-critical + wrong
    empathy_bonus: float = 0.0  # Amount added for empathetic response
    
    # Overall
    weighted_score: float  # Final composite score
    task_type: str  # 'classify', 'route', or 'resolve'
    
    # Actionable feedback
    what_went_right: list[str]  # Things agent got correct
    what_went_wrong: list[str]  # Things agent missed
    suggestions: list[str]  # How to improve next time


class RuleBasedGrader:
    """
    Deterministic rule-based grader for training agents.
    
    Features:
    - No API calls (fast)
    - Reproducible across runs
    - Component-level feedback
    - Clear reasoning for each decision
    - Designed for LLM agent learning
    """
    
    def __init__(self, config: Dict[str, Any] | None = None):
        """Initialize with optional configuration."""
        self.config = config or {}
        
    def grade_classify(
        self,
        predicted_category: str,
        predicted_priority: str,
        ground_truth_category: str,
        ground_truth_priority: str,
        customer_tier: str = "free",
    ) -> DetailedScoreBreakdown:
        """Grade a classify action with detailed component breakdown.
        
        Returns:
            DetailedScoreBreakdown with component scores and feedback
        """
        # Category scoring
        category_correct = predicted_category.lower() == ground_truth_category.lower()
        category_score = _strict_unit_score(0.95 if category_correct else 0.3)
        
        # Priority scoring (graduated scale)
        priority_correct = predicted_priority.lower() == ground_truth_priority.lower()
        if priority_correct:
            priority_score = _strict_unit_score(0.95)
            priority_reasoning = "Priority classification is exact match"
        else:
            # Check if one step off
            priority_order = ["low", "medium", "high", "urgent"]
            try:
                predicted_idx = priority_order.index(predicted_priority.lower())
                ground_idx = priority_order.index(ground_truth_priority.lower())
                distance = abs(predicted_idx - ground_idx)
                
                if distance == 1:
                    priority_score = _strict_unit_score(0.6)
                    priority_reasoning = f"Priority is close but not exact (1 step: {predicted_priority} vs {ground_truth_priority})"
                else:
                    priority_score = _strict_unit_score(0.2)
                    priority_reasoning = f"Priority is off by {distance} steps ({predicted_priority} vs {ground_truth_priority})"
            except ValueError:
                priority_score = _strict_unit_score(0.1)
                priority_reasoning = f"Priority '{predicted_priority}' is invalid/unrecognized"
        
        # Enterprise penalty
        enterprise_penalty = 0.0
        if customer_tier.lower() == "enterprise" and not priority_correct:
            enterprise_penalty = 0.15  # Enterprise customers are penalized more
        
        # Composite score with weights
        category_weight = 0.6
        priority_weight = 0.4
        weighted_score = _strict_unit_score(
            (category_score * category_weight + priority_score * priority_weight) - enterprise_penalty
        )
        
        # Feedback
        what_went_right = []
        what_went_wrong = []
        suggestions = []
        
        if category_correct:
            what_went_right.append(f"✓ Correctly identified category: {ground_truth_category}")
        else:
            what_went_wrong.append(f"✗ Category: predicted '{predicted_category}', should be '{ground_truth_category}'")
            suggestions.append(f"Look for keywords that indicate {ground_truth_category} issues")
        
        if priority_correct:
            what_went_right.append(f"✓ Correctly assigned priority: {ground_truth_priority}")
        else:
            what_went_wrong.append(f"✗ Priority: predicted '{predicted_priority}', should be '{ground_truth_priority}'")
            if customer_tier.lower() == "enterprise":
                suggestions.append("This is an ENTERPRISE customer - priority errors are heavily penalized")
            suggestions.append(f"Look for urgency indicators (SLA, customer type) suggesting {ground_truth_priority}")
        
        return DetailedScoreBreakdown(
            category_score=ScoreComponent(
                value=category_score,
                weight=category_weight,
                reasoning="Classification correctness",
            ),
            priority_score=ScoreComponent(
                value=priority_score,
                weight=priority_weight,
                reasoning=priority_reasoning,
            ),
            enterprise_penalty=enterprise_penalty,
            weighted_score=weighted_score,
            task_type="classify",
            what_went_right=what_went_right,
            what_went_wrong=what_went_wrong,
            suggestions=suggestions,
        )
    
    def grade_route(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any],
        ticket_metadata: Dict[str, Any] | None = None,
    ) -> DetailedScoreBreakdown:
        """Grade a route action with detailed component breakdown."""
        ticket_metadata = ticket_metadata or {}
        customer_tier = ticket_metadata.get("tier", "free")
        open_since_hours = ticket_metadata.get("open_since_hours", 0)
        
        # Component scores
        category_correct = predicted["category"].lower() == ground_truth["category"].lower()
        category_score = _strict_unit_score(0.95 if category_correct else 0.3)
        
        # Priority (graduated)
        priority_order = ["low", "medium", "high", "urgent"]
        priority_correct = predicted["priority"].lower() == ground_truth["priority"].lower()
        try:
            pred_idx = priority_order.index(predicted["priority"].lower())
            gt_idx = priority_order.index(ground_truth["priority"].lower())
            priority_score = _strict_unit_score(0.95 - abs(pred_idx - gt_idx) * 0.25)
        except ValueError:
            priority_score = _strict_unit_score(0.1)
        
        # Department (with fallback credit)
        department_correct = predicted["department"].lower() == ground_truth["department"].lower()
        if department_correct:
            department_score = _strict_unit_score(0.95)
            department_reasoning = "Correct department routing"
        else:
            # Check for reasonable fallback
            pred_dept = predicted["department"].lower()
            gt_dept = ground_truth["department"].lower()
            
            # tier1 → tier2 is acceptable fallback
            is_fallback = (pred_dept == "tier1" and gt_dept == "tier2") or \
                         (pred_dept == "tier2" and gt_dept == "engineering")
            
            if is_fallback:
                department_score = _strict_unit_score(0.4)
                department_reasoning = "Department is reasonable fallback"
            else:
                department_score = _strict_unit_score(0.1)
                department_reasoning = f"Wrong department ({pred_dept} vs {gt_dept})"
        
        # Escalation
        escalation_correct = predicted.get("requires_escalation", False) == ground_truth.get("requires_escalation", False)
        escalation_score = _strict_unit_score(0.95 if escalation_correct else 0.3)
        
        # Penalties
        enterprise_penalty = 0.0 if priority_correct else (0.20 if customer_tier == "enterprise" else 0.0)
        sla_penalty = 0.0 if priority_correct else (0.15 if open_since_hours > 24 else 0.0)
        
        # Weights
        weights = {
            "category": 0.35,
            "priority": 0.25,
            "department": 0.25,
            "escalation": 0.15,
        }
        
        weighted_score = _strict_unit_score(
            (category_score * weights["category"] +
             priority_score * weights["priority"] +
             department_score * weights["department"] +
             escalation_score * weights["escalation"]) -
            enterprise_penalty - sla_penalty
        )
        
        # Feedback
        what_went_right = []
        what_went_wrong = []
        suggestions = []
        
        if category_correct:
            what_went_right.append(f"✓ Category correct: {ground_truth['category']}")
        else:
            what_went_wrong.append(f"✗ Category wrong: {predicted['category']} vs {ground_truth['category']}")
        
        if priority_correct:
            what_went_right.append(f"✓ Priority correct: {ground_truth['priority']}")
        else:
            what_went_wrong.append(f"✗ Priority wrong: {predicted['priority']} vs {ground_truth['priority']}")
            if open_since_hours > 24:
                suggestions.append("ALERT: Ticket is SLA-critical (open >24h) - priority errors are heavily penalized")
        
        if department_correct:
            what_went_right.append(f"✓ Department correct: {ground_truth['department']}")
        else:
            what_went_wrong.append(f"✗ Department wrong: {predicted['department']} vs {ground_truth['department']}")
            suggestions.append(f"Route to {ground_truth['department']} based on ticket type and complexity")
        
        if escalation_correct:
            what_went_right.append(f"✓ Escalation judgment correct: {ground_truth.get('requires_escalation', False)}")
        else:
            what_went_wrong.append(f"✗ Escalation wrong: predicted {predicted.get('requires_escalation', False)}")
        
        return DetailedScoreBreakdown(
            category_score=ScoreComponent(value=category_score, weight=weights["category"], reasoning="Category classification"),
            priority_score=ScoreComponent(value=priority_score, weight=weights["priority"], reasoning="Priority level assessment"),
            department_score=ScoreComponent(value=department_score, weight=weights["department"], reasoning=department_reasoning),
            escalation_score=ScoreComponent(value=escalation_score, weight=weights["escalation"], reasoning="Escalation judgment"),
            enterprise_penalty=enterprise_penalty,
            sla_penalty=sla_penalty,
            weighted_score=weighted_score,
            task_type="route",
            what_went_right=what_went_right,
            what_went_wrong=what_went_wrong,
            suggestions=suggestions,
        )
    
    def grade_resolve(
        self,
        predicted: Dict[str, Any],
        ground_truth: Dict[str, Any],
        ticket_metadata: Dict[str, Any] | None = None,
    ) -> DetailedScoreBreakdown:
        """Grade a resolve action with detailed response quality analysis.
        
        IMPROVED: Uses semantic evaluation as primary method for response quality.
        Falls back to keyword-based evaluation if semantic is unavailable.
        """
        ticket_metadata = ticket_metadata or {}
        
        # Grade core components first (reuse route grading for those)
        route_breakdown = self.grade_route(predicted, ground_truth, ticket_metadata)
        
        # Response quality - PRIORITIZE SEMANTIC EVALUATION
        response = (predicted.get("response") or "").strip()
        gt_keywords = ticket_metadata.get("response_keywords", [])
        empathy_bonus = 0.0  # Initialize before conditional branches to prevent NameError
        
        if not response or len(response) < 20:
            response_score = _strict_unit_score(0.1)
            keyword_reasoning = "Response too short or missing"
            keywords_found = 0
        else:
            # PRIMARY: Try semantic evaluation (measures actual quality, not just keyword presence)
            evaluator = get_semantic_evaluator()
            
            if evaluator and evaluator.enabled:
                # Use semantic evaluation - more robust against keyword gaming
                logger.info("Using semantic evaluation for response quality")
                
                # Build ideal responses based on ticket metadata
                ticket_sentiment = ticket_metadata.get("sentiment", "neutral")
                ticket_category = ground_truth.get("category", "general")
                
                # Generic ideal response templates (basic - could be expanded)
                ideal_responses = [
                    "Thank you for contacting us. We understand your concern and will investigate this immediately.",
                    "We appreciate you bringing this to our attention. We will process this right away.",
                    "Thank you for your patience. We are working on resolving your issue and will follow up shortly.",
                ]
                
                # Evaluate semantic similarity
                eval_result = evaluator.evaluate_response(
                    response=response,
                    ideal_responses=ideal_responses,
                    required_keywords=gt_keywords if gt_keywords else None,
                )
                
                response_score = _strict_unit_score(eval_result.get("combined_score", 0.5))
                keyword_reasoning = eval_result.get("reasoning", "Semantic evaluation")
                keywords_found = int(eval_result.get("keyword_coverage", 0) * len(gt_keywords)) if gt_keywords else 0
                
                # Empathy bonus for frustrated customers (semantic-aware)
                has_empathy = any(word in response.lower() for word in ["sorry", "understand", "apologize", "appreciate"])
                if has_empathy and ticket_sentiment in ["frustrated", "angry"]:
                    response_score = _strict_unit_score(min(0.99, response_score + 0.1))
                    empathy_bonus = 0.1
            
            else:
                # FALLBACK: Keyword-based evaluation (if semantic unavailable)
                logger.warning("Semantic evaluator not available, falling back to keyword-based evaluation")
                
                response_lower = response.lower()
                # Use morphological term variants for better keyword matching
                response_terms = {
                    variant
                    for token in response_lower.split()
                    for variant in _term_variants(token)
                }
                
                def _kw_match(kw: str) -> bool:
                    return bool(_term_variants(kw) & response_terms)
                
                keywords_found = sum(1 for kw in gt_keywords if _kw_match(kw))
                keyword_coverage = keywords_found / max(1, len(gt_keywords))
                
                # Response quality heuristics
                has_action_phrases = any(phrase in response_lower for phrase in ["will", "process", "send", "provide"])
                has_empathy = any(word in response_lower for word in ["understand", "sorry", "appreciate", "thank"])
                
                base_response_score = _strict_unit_score(0.3 + keyword_coverage * 0.6 + (0.1 if has_action_phrases else 0))
                
                # Empathy bonus for frustrated customers
                empathy_bonus = 0.1 if has_empathy and ticket_metadata.get("sentiment") == "frustrated" else 0.0
                response_score = _strict_unit_score(base_response_score + empathy_bonus)
                
                keyword_reasoning = f"Found {keywords_found}/{len(gt_keywords)} required keywords ({keyword_coverage:.0%} coverage)"
        
        # Weights for resolve task are heavier on response
        weights = {
            "category": 0.15,
            "priority": 0.15,
            "department": 0.15,
            "escalation": 0.15,
            "response": 0.4,  # Response is most important for resolve
        }
        
        # Recalculate weighted score including response
        weighted_score = _strict_unit_score(
            (route_breakdown.category_score.value * weights["category"] +
             route_breakdown.priority_score.value * weights["priority"] +
             (route_breakdown.department_score.value if route_breakdown.department_score else 0.5) * weights["department"] +
             (route_breakdown.escalation_score.value if route_breakdown.escalation_score else 0.5) * weights["escalation"] +
             response_score * weights["response"]) -
            route_breakdown.enterprise_penalty - route_breakdown.sla_penalty
        )
        
        # Feedback
        what_went_right = route_breakdown.what_went_right.copy()
        what_went_wrong = route_breakdown.what_went_wrong.copy()
        suggestions = route_breakdown.suggestions.copy()
        
        if response and len(response) > 20:
            what_went_right.append(f"✓ Response provided ({len(response)} characters)")
            if keywords_found > 0:
                what_went_right.append(f"✓ Included {keywords_found} of {len(gt_keywords)} key topics")
        else:
            what_went_wrong.append("✗ Response is missing or too short (<20 chars)")
            suggestions.append("Provide a professional response addressing the customer's issue")
        
        return DetailedScoreBreakdown(
            category_score=route_breakdown.category_score,
            priority_score=route_breakdown.priority_score,
            department_score=route_breakdown.department_score,
            escalation_score=route_breakdown.escalation_score,
            response_score=ScoreComponent(
                value=response_score,
                weight=weights["response"],
                reasoning=keyword_reasoning,
            ),
            enterprise_penalty=route_breakdown.enterprise_penalty,
            sla_penalty=route_breakdown.sla_penalty,
            empathy_bonus=empathy_bonus,
            weighted_score=weighted_score,
            task_type="resolve",
            what_went_right=what_went_right,
            what_went_wrong=what_went_wrong,
            suggestions=suggestions,
        )
