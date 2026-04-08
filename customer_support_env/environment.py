"""Customer support RL environment: the core game logic."""

import logging
import random
import re
import uuid
from typing import Dict, Any

from .openenv_compat import Environment

from .models import StepInfo, TicketAction, TicketObservation, TicketReward, TicketState
from .data import TICKET_DATA, get_ticket_labels
from .rule_based_grader import RuleBasedGrader, DetailedScoreBreakdown
from .reward_config import RewardConfig
from .curriculum_manager import CurriculumManager
from .semantic_evaluator import get_semantic_evaluator

# Configure logging
logger = logging.getLogger(__name__)

_STRICT_SCORE_EPSILON = 0.001


def _strict_unit_score(value: float) -> float:
    """Clamp a score to the open interval (0, 1) with stable rounding."""
    return round(min(1.0 - _STRICT_SCORE_EPSILON, max(_STRICT_SCORE_EPSILON, value)), 3)


def _validate_strict_score(score: float, label: str = "score") -> float:
    """Validate and clamp a score to be strictly in (0, 1).
    
    DEFENSIVE: This function ensures NO score ever escapes unclamped.
    
    Args:
        score: The score to validate
        label: Description for logging
    
    Returns:
        Score strictly in (0.001, 0.999)
    
    Raises:
        ValueError: If score is NaN or invalid
    """
    # Check for invalid values
    if not isinstance(score, (int, float)):
        logger.error(f"❌ INVALID SCORE TYPE: {label}={score} (type={type(score).__name__})")
        return _STRICT_SCORE_EPSILON
    
    if score != score:  # NaN check
        logger.error(f"❌ NaN DETECTED: {label}={score}, using epsilon")
        return _STRICT_SCORE_EPSILON
    
    if score == float('inf') or score == float('-inf'):
        logger.error(f"❌ INFINITE SCORE: {label}={score}, using bound")
        return _strict_unit_score(0.5)
    
    # Clamp to strict bounds
    clamped = _strict_unit_score(score)
    
    # Defensive logging: warn if score was exactly 0.0 or 1.0
    if score == 0.0:
        logger.warning(f"⚠️  CLAMPED 0.0 → {clamped}: {label}")
    elif score == 1.0:
        logger.warning(f"⚠️  CLAMPED 1.0 → {clamped}: {label}")
    elif abs(score - clamped) > 0.001:
        logger.warning(f"⚠️  CLAMPED {score:.4f} → {clamped}: {label}")
    
    # Final validation: ensure result is strictly in (0, 1)
    if clamped <= 0.0 or clamped >= 1.0:
        logger.critical(f"❌ VALIDATION FAILED: {label}={clamped} is not strictly in (0, 1)")
        # Emergency fallback
        return 0.5
    
    return clamped


def _term_variants(term: str) -> set[str]:
    """Generate normalized variants of a term for keyword matching.
    
    Handles English inflections including silent-e rule:
    - resolve + ed → resolved (drop silent(e)
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


class CustomerSupportEnvironment(Environment[TicketAction, TicketObservation, TicketState]):
    """Customer support ticket environment with trajectory-shaped rewards.

    Design:
    - reset() picks a ticket and task
    - step() supports task-dependent multi-step trajectories
    - reward provides partial progress, loop penalties, and time penalties
    """
    
    SUPPORTS_CONCURRENT_SESSIONS = True
    
    # Priority ordering for graduated scoring
    PRIORITY_ORDER = ["low", "medium", "high", "urgent"]
    
    # Task difficulty mapping
    DIFFICULTY_MAP = {
        "classify": "easy",
        "route": "medium",
        "resolve": "hard",
    }
    
    # ============= GRADING CONFIGURATION PARAMETERS =============
    # These constants control how actions are scored. Tune these to adjust difficulty.
    
    # Enterprise customer handling: penalize priority mistakes more for enterprise customers
    ENTERPRISE_PRIORITY_PENALTY = 0.7  # Multiply score by this if enterprise + wrong priority
    
    # SLA urgency modeling: tickets open > 24h are SLA-critical
    SLA_THRESHOLD_HOURS = 24
    SLA_PENALTY_MULTIPLIER = 0.85  # Applied when SLA-critical + priority wrong
    
    # Response quality requirements (resolve task)
    RESPONSE_MIN_LENGTH = 20  # Minimum characters to count as valid response
    RESPONSE_LENGTH_PENALTY = 0.5  # Penalty multiplier if response too short
    RESPONSE_KEYWORD_THRESHOLD = 0.5   # Must match at least half of the required keywords
    RESPONSE_MIN_KEYWORDS_REQUIRED = 3  # Minimum keywords needed regardless of threshold
    
    # Response content penalties
    RESPONSE_ACTION_PHRASE_PENALTY = 0.1  # Reduce score if no concrete action phrases
    RESPONSE_FILLER_PENALTY = 0.3  # Reduce score if mostly filler content

    # Trajectory shaping penalties
    LOOP_PENALTY = 0.15
    EXTRA_STEP_PENALTY = 0.05
    
    # Sentiment-aware response bonuses
    SENTIMENT_EMPATHY_BONUS = 0.1  # Bonus for empathetic response when frustrated customer
    
    # Department fallback scoring (allow partial credit for reasonable alternatives)
    DEPARTMENT_FALLBACK_SCORE = 0.4  # Score for tier1 → tier2 or tier2 ↔ engineering
    DEPARTMENT_EXACT_SCORE = 1.0  # Score for exact match
    
    # Priority distance scoring
    PRIORITY_EXACT_SCORE = 1.0
    
    # Max trajectory length by task difficulty.
    TASK_MAX_STEPS = {
        "classify": 1,
        "route": 2,
        "resolve": 3,
    }
    PRIORITY_ONE_STEP_SCORE = 0.6
    PRIORITY_TWO_STEP_SCORE = 0.2
    PRIORITY_THREE_PLUS_STEP_SCORE = 0.0
    
    # Reward weights per task (updated to include escalation)
    REWARD_WEIGHTS = {
        "classify": {"category": 0.6, "priority": 0.4},
        "route": {"category": 0.35, "priority": 0.25, "department": 0.25, "escalation": 0.15},
        "resolve": {"category": 0.2, "priority": 0.15, "department": 0.2, "escalation": 0.15, "response": 0.3},
    }
    
    # Action schema definitions shown to agent (now with examples)
    ACTION_SCHEMAS = {
        "classify": """{
  "category": "string (required): billing | technical | account | general | shipping",
  "priority": "string (required): low | medium | high | urgent"
}

Example output:
{"category": "billing", "priority": "high"}""",
        "route": """{
  "category": "string (required): billing | technical | account | general | shipping",
  "priority": "string (required): low | medium | high | urgent",
  "department": "string (required): tier1 | tier2 | billing | engineering | management",
  "requires_escalation": "boolean (optional): true if supervisor review needed"
}

Example output:
{"category": "technical", "priority": "high", "department": "engineering", "requires_escalation": false}""",
        "resolve": """{
  "category": "string (required): billing | technical | account | general | shipping",
  "priority": "string (required): low | medium | high | urgent",
  "department": "string (required): tier1 | tier2 | billing | engineering | management",
  "requires_escalation": "boolean (optional): true if supervisor review needed",
  "response": "string (required): Professional customer-facing response message"
}

Example output:
{"category": "billing", "priority": "medium", "department": "billing", "requires_escalation": false, "response": "Thank you for contacting us. We've reviewed your refund request..."}""",
    }
    
    # Task descriptions
    TASK_DESCRIPTIONS = {
        "classify": "Read the customer's ticket and classify it into a category (billing, technical, account, general, or shipping) and assign a priority level (low, medium, high, urgent).",
        "route": "Read the customer's ticket, classify it, assign priority, and determine which department should handle it (tier1, tier2, billing, engineering, or management).",
        "resolve": "Read the customer's ticket, classify it, assign priority, route it to the right department, and draft a professional response addressing their issue.",
    }
    
    # Routing policy that applies to all tasks
    ROUTING_POLICY = """
DEPARTMENT ROUTING POLICY:
- tier1: General questions, FAQ answers, simple troubleshooting, standard refunds (low complexity)
- tier2: Complex technical issues, account investigations, escalation preparation (medium complexity)
- billing: Payment disputes, subscription changes, invoice corrections, refund processing
- engineering: Bug reports, API errors, performance problems, feature requests
- management: VIP retention, compliance/legal matters, contract disputes, security incidents

ESCALATION CRITERIA (requires_escalation=true):
  • Enterprise customer + financial/trust issue
  • Security incident
  • Customer threatening churn
  • Policy exception required
"""
    
    # Policy excerpts for resolve task
    POLICY_EXCERPTS = {
        "billing": "Refund Policy: We offer full refunds within 14 days of purchase for any reason. After 14 days, refunds are issued pro-rated for unused time. Billing errors are corrected immediately with refunds within 3 business days.",
        "technical": "Technical SLA: Critical issues (P1) receive response within 1 hour. High priority (P2) within 4 hours. Medium priority (P3) within 1 business day. We provide product documentation, API debugging, and troubleshooting support.",
        "account": "Account Policy: Users can cancel anytime without penalty. Account deletion is processed within 14 days with complete data removal. Enterprise accounts require management approval.",
        "general": "Company Values: We prioritize customer success, transparency, and community. Partnership opportunities are reviewed by our business development team. Security vulnerabilities are handled as P0 with immediate investigation.",
        "shipping": "Shipping Policy: Orders ship within 2 business days. Free shipping for orders over $50, expedited available for $10. Lost packages are replaced or refunded within 7 business days.",
    }
    
    def __init__(self) -> None:
        """Initialize environment state variables and new AI training components.
        
        Initializes:
        - Rule-based grader (primary training grading)
        - Reward config (parameterized reward shaping)
        - Curriculum manager (progressive difficulty)
        - Semantic evaluator (response quality scoring)
        """
        # Validate reward weights sum to 1.0 for each task
        for task, weights in self.REWARD_WEIGHTS.items():
            total_weight = sum(weights.values())
            if abs(total_weight - 1.0) >= 1e-9:
                raise ValueError(
                    f"REWARD_WEIGHTS['{task}'] sum to {total_weight}, not 1.0. "
                    f"Weights: {weights}"
                )
        
        # Initialize new AI training components
        self._grader = RuleBasedGrader()
        self._reward_config = RewardConfig.preset_medium()  # Default: medium difficulty
        self._curriculum = CurriculumManager()
        self._evaluator = get_semantic_evaluator()
        
        self._state: TicketState = TicketState()
        self._ticket: Dict[str, Any] | None = None
        self._task: str = "classify"
    
    def reset(self, seed=None, episode_id=None, task="classify", **kwargs) -> TicketObservation:
        """Reset environment for new episode: pick ticket, set task, initialize state.

        NOTE: Labels are NOT passed in observations (prevents memorization via seeding).
        Ground truth is stored separately and only accessible to graders.

        Args:
            seed: Random seed for reproducibility (NOT used to index tickets directly!)
            episode_id: Episode identifier (generated if not provided)
            task: "classify", "route", or "resolve"
            
        Returns:
            Initial observation with done=False, reward=None (no ground truth exposed)
        """
        # Step 1: Pick a ticket using seed as RNG seed (not direct index)
        # This prevents agents from memorizing: "seed=5 → category=billing"
        rng = random.Random(seed) if seed is not None else random.Random()
        self._ticket = rng.choice(TICKET_DATA)
        
        self._task = task
        
        # Step 2: Initialize fresh state (no carryover from previous episode)
        self._state = TicketState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            task_name=task,
            difficulty=self.DIFFICULTY_MAP[task],
            max_steps=self.TASK_MAX_STEPS[task],
            best_score=0.0,
            cumulative_reward=0.0,
        )
        
        # Step 3: Return initial observation
        if self._ticket is None:
            raise RuntimeError("reset() must be called before step()")
        
        # Build policy excerpt: routing policy only (do NOT expose category-specific policy yet!)
        # This prevents implicit hints about the ticket category
        policy_excerpt = self.ROUTING_POLICY
        
        return TicketObservation(
            ticket_id=self._ticket["id"],
            subject=self._ticket["subject"],
            body=self._ticket["body"],
            sender_tier=self._ticket["tier"],
            open_since_hours=self._ticket.get("open_since_hours", 0),
            sentiment=self._ticket.get("sentiment", "neutral"),
            task_name=task,
            task_description=self.TASK_DESCRIPTIONS[task],
            action_schema=self.ACTION_SCHEMAS[task],
            policy_excerpt=policy_excerpt,
            feedback="",  # No feedback on initial reset
            previous_tickets=self._ticket.get("previous_tickets", 0),
            done=False,  # Explicitly False on reset
            reward=None,  # No reward yet on reset
        )
    
    def step(self, action: TicketAction, timeout_s=None, **kwargs) -> tuple[TicketObservation, float, bool, dict]:
        """Process one action, grade it, return score and feedback.

        Multi-step: done depends on task max steps or near-perfect completion.
        
        Args:
            action: Agent's TicketAction response
            timeout_s: Optional timeout (unused in single-turn)
            
        Returns:
            A 4-tuple of (observation, reward, done, info)
        """
        if self._ticket is None:
            raise RuntimeError("reset() must be called before step()")

        self._state.step_count += 1

        # Enforce task-specific action requirements early.
        action.validate_for_task(self._task)
        
        # Try to grade, gracefully handle malformed actions
        reward_model: TicketReward
        breakdown: DetailedScoreBreakdown
        try:
            raw_score, breakdown = self._grade(action)
            reward_model = self.build_reward(action, raw_score)
            feedback = self._build_feedback(action, raw_score, breakdown)
        except Exception as e:
            logger.exception("Unexpected grading failure for task %s", self._task)
            raise

        reward = reward_model.value
        self._state.cumulative_reward = round(self._state.cumulative_reward + reward, 3)
        self._state.best_score = round(max(self._state.best_score, raw_score), 3)
        self._state.action_history.append(self._action_signature(action))
        done = self._compute_done(raw_score)
        
        # Return final observation: single-turn always done after one step
        # NOTE: Do NOT include category-specific policy excerpt!
        # Category-specific hints would allow agents to infer the ground truth category from the policy alone.
        # This protects against label leakage.
        policy_excerpt = self.ROUTING_POLICY
        
        observation = TicketObservation(
            ticket_id=self._ticket["id"],
            subject=self._ticket["subject"],
            body=self._ticket["body"],
            sender_tier=self._ticket["tier"],
            open_since_hours=self._ticket.get("open_since_hours", 0),
            sentiment=self._ticket.get("sentiment", "neutral"),
            task_name=self._task,
            task_description=self.TASK_DESCRIPTIONS[self._task],
            action_schema=self.ACTION_SCHEMAS[self._task],
            policy_excerpt=policy_excerpt,
            feedback=feedback,
            previous_tickets=self._ticket.get("previous_tickets", 0),
            done=done,
            reward=reward,
        )

        info = StepInfo(
            step_count=self._state.step_count,
            max_steps=self._state.max_steps,
            best_score=self._state.best_score,
            cumulative_reward=self._state.cumulative_reward,
        ).model_dump()
        
        # Defensive: Validate raw score before adding to info
        validated_raw_score = _validate_strict_score(raw_score, f"step_raw_score[ticket={self._ticket.get('id', 'UNKNOWN')}]")
        
        info.update(
            {
                "raw_score": validated_raw_score,
                "feedback": feedback,
                "reward_breakdown": reward_model.model_dump(),
            }
        )

        return observation, reward, done, info

    def state(self) -> TicketState:
        """Return current state for OpenEnv compatibility."""
        return self._state

    def _compute_done(self, raw_score: float) -> bool:
        if raw_score >= 0.95:
            return True
        return self._state.step_count >= self._state.max_steps

    def build_reward(self, action: TicketAction, raw_score: float) -> TicketReward:
        """Build a typed reward model with transparent shaping components.
        
        DEFENSIVE: All components are validated to be strictly in (0, 1).
        Phase 2: ALL numeric values must be strictly in (0, 1).
        """
        prev_best = self._state.best_score
        progress_gain = max(0.0, raw_score - prev_best)
        step_penalty = self.EXTRA_STEP_PENALTY * max(0, self._state.step_count - 1)
        loop_penalty = self.LOOP_PENALTY if self._action_signature(action) in self._state.action_history else 0.0
        final_reward_raw = max(0.0, progress_gain - step_penalty - loop_penalty)
        
        # Comprehensive validation of all components
        # Phase 2 requirement: ALL numeric values must be strictly in (0, 1)
        _EPS = 0.001
        final_value = round(max(_EPS, min(1.0 - _EPS, float(final_reward_raw))), 4)
        value = _validate_strict_score(final_value, "reward_value")
        raw_score_clamped = _validate_strict_score(raw_score, "raw_score_component")
        progress_gain_clamped = _validate_strict_score(progress_gain, "progress_gain")
        step_penalty_clamped = _validate_strict_score(step_penalty, "extra_step_penalty")
        loop_penalty_clamped = _validate_strict_score(loop_penalty, "repeated_action_penalty")
        
        return TicketReward(
            value=value,
            raw_score=raw_score_clamped,
            progress_gain=progress_gain_clamped,  # Strictly in (0, 1)
            repeated_action_penalty=loop_penalty_clamped,  # Strictly in (0, 1)
            extra_step_penalty=step_penalty_clamped,  # Strictly in (0, 1)
        )

    def _action_signature(self, action: TicketAction) -> str:
        response = (action.response or "").strip().lower()
        response = re.sub(r"\s+", " ", response)
        return "|".join(
            [
                (action.category or "").strip().lower(),
                (action.priority or "").strip().lower(),
                (action.department or "").strip().lower(),
                str(bool(action.requires_escalation)).lower(),
                response,
            ]
        )
    
    def _grade(self, action: TicketAction) -> tuple[float, DetailedScoreBreakdown]:
        """Score the action using rule-based grader with component-level feedback.
        
        PRIMARY GRADING: Uses RuleBasedGrader for deterministic, transparent scoring
        instead of OpenAI API. This provides:
        - Component-level feedback (category, priority, department, escalation, response)
        - Actionable suggestions (what-went-right, what-went-wrong, next steps)
        - No external API dependencies (fast, cost-free)
        - Deterministic results (same input = same output)
        
        Returns:
            Tuple of (overall_score, detailed_breakdown)
            - overall_score: float in (0.001, 0.999) after Phase 2 clamping
            - detailed_breakdown: DetailedScoreBreakdown with component scores and feedback
        """
        if self._ticket is None:
            raise RuntimeError("reset() must be called before step()")
        
        # Prepare inputs
        customer_tier = self._ticket.get("tier", "free")
        
        # Predicted values (normalized)
        pred_category = (action.category or "").strip().lower()
        pred_priority = (action.priority or "").strip().lower()
        pred_department = (action.department or "").strip().lower()
        pred_escalation = action.requires_escalation or False
        response = (action.response or "").strip()
        
        ticket_id = self._ticket.get("id", "UNKNOWN")
        logger.debug(f"Grading action for ticket {ticket_id} (task={self._task})")
        
        # Build action dict for grader
        action_dict = {
            "category": pred_category,
            "priority": pred_priority,
            "department": pred_department,
            "requires_escalation": pred_escalation,
            "response": response,
        }
        
        # CRITICAL FIX: Get ground truth from labels (NOT from observation!)
        # This prevents label leakage - agents cannot infer labels from seeds
        labels = get_ticket_labels(ticket_id)
        gt_dict = {
            "category": labels.get("category", "general"),
            "priority": labels.get("priority", "medium"),
            "department": labels.get("department", "tier1"),
            "requires_escalation": labels.get("requires_escalation", False),
        }
        
        # Ticket metadata
        metadata = {
            "tier": customer_tier,
            "open_since_hours": self._ticket.get("open_since_hours", 0),
            "sentiment": self._ticket.get("sentiment", "neutral"),
            "response_keywords": self._ticket.get("response_keywords", []),
        }
        
        # STEP 1: Use RuleBasedGrader for component-level feedback
        if self._task == "classify":
            breakdown = self._grader.grade_classify(
                predicted_category=pred_category,
                predicted_priority=pred_priority,
                ground_truth_category=gt_dict["category"],
                ground_truth_priority=gt_dict["priority"],
                customer_tier=customer_tier,
            )
        
        elif self._task == "route":
            breakdown = self._grader.grade_route(
                predicted=action_dict,
                ground_truth=gt_dict,
                ticket_metadata=metadata,
            )
        
        else:  # resolve (HARD task)
            breakdown = self._grader.grade_resolve(
                predicted=action_dict,
                ground_truth=gt_dict,
                ticket_metadata=metadata,
            )
        
        # STEP 2: Get final score (already clamped by RuleBasedGrader)
        final_score = breakdown.weighted_score
        
        logger.info(f"✅ Grade for ticket {ticket_id} ({self._task}): {final_score:.3f}")
        logger.debug(f"  Component breakdown: {breakdown}")
        
        # STEP 3: Validate strict bounds (Phase 2 compliance)
        final_score = _validate_strict_score(final_score, f"final_score[ticket={ticket_id}]")
        
        # Return both score and detailed breakdown
        return final_score, breakdown
    
    def _build_feedback(self, action: TicketAction, score: float, breakdown: DetailedScoreBreakdown | None = None) -> str:
        """Build human-readable explanation of the grade with AI assistance.
        
        Now integrates component-level feedback from RuleBasedGrader breakdown.
        
        Includes:
        - Rule-based component scores (category, priority, department, etc.)
        - What-went-right / what-went-wrong / suggestions from breakdown
        - Escalation judgment assessment
        - Response quality feedback (if resolve task)
        - Overall quality rating
        
        Used for grading transparency and debugging.
        """
        if self._ticket is None:
            raise RuntimeError("reset() must be called before step()")
        
        # Use breakdown feedback if available, otherwise build it manually
        if breakdown:
            # Use the detailed feedback from rule-based grader
            feedback_parts = []
            
            # Add component-level feedback
            if breakdown.what_went_right:
                feedback_parts.append(f"✓ {breakdown.what_went_right}")
            
            if breakdown.what_went_wrong:
                feedback_parts.append(f"✗ {breakdown.what_went_wrong}")
            
            if breakdown.suggestions:
                feedback_parts.append(f"💡 {breakdown.suggestions}")
            
            base_feedback = " | ".join(feedback_parts) if feedback_parts else f"Score: {score:.2f}"
        else:
            # Fallback to manual feedback building (legacy behavior)
            # CRITICAL: Use get_ticket_labels() NOT self._ticket for ground truth!
            ticket_id = self._ticket.get("id", "UNKNOWN")
            labels = get_ticket_labels(ticket_id)
            gt_category = labels.get("category", "general")
            gt_priority = labels.get("priority", "medium")
            gt_department = labels.get("department", "tier1")
            gt_escalation = labels.get("requires_escalation", False)
            
            pred_category = (action.category or "").strip().lower()
            pred_priority = (action.priority or "").strip().lower()
            pred_department = (action.department or "").strip().lower()
            
            feedback_parts = []
            
            # Category feedback
            if pred_category.lower() == gt_category.lower():
                feedback_parts.append(f"✓ Category correct: {gt_category}")
            else:
                feedback_parts.append(f"✗ Category: '{action.category}' (expected '{gt_category}')")
            
            # Priority feedback with distance info
            if pred_priority.lower() == gt_priority.lower():
                feedback_parts.append(f"✓ Priority correct: {gt_priority}")
            else:
                try:
                    distance = abs(
                        self.PRIORITY_ORDER.index(pred_priority) -
                        self.PRIORITY_ORDER.index(gt_priority)
                    )
                    if distance == 1:
                        feedback_parts.append(f"~ Priority close: '{action.priority}' vs '{gt_priority}' (1 step)")
                    else:
                        feedback_parts.append(f"✗ Priority: '{action.priority}' (expected '{gt_priority}')")
                except ValueError:
                    feedback_parts.append(f"✗ Priority: invalid '{action.priority}' (expected '{gt_priority}')")
            
            # Department feedback (if task requires it)
            if self._task in ["route", "resolve"]:
                if pred_department.lower() == gt_department.lower():
                    feedback_parts.append(f"✓ Department correct: {gt_department}")
                else:
                    feedback_parts.append(f"✗ Department: '{action.department}' (expected '{gt_department}')")
            
            # Escalation feedback (if task requires it)
            if self._task in ["route", "resolve"]:
                if action.requires_escalation == gt_escalation:
                    feedback_parts.append(f"✓ Escalation judgment correct: {gt_escalation}")
                else:
                    feedback_parts.append(f"✗ Escalation: {action.requires_escalation} (expected {gt_escalation})")
            
            # Overall score context
            if score >= 0.9:
                quality = "Excellent"
            elif score >= 0.7:
                quality = "Good"
            elif score >= 0.5:
                quality = "Partial"
            else:
                quality = "Needs improvement"
            
            base_feedback = f"{' | '.join(feedback_parts)} | Score: {quality} ({score:.2f})"
        
        # Optionally add AI-generated constructive feedback
        try:
            from .openai_integration import get_openai_integration
            openai = get_openai_integration()
            if openai and openai.enabled and self._ticket:
                try:
                    ai_feedback = openai.generate_feedback(
                        score=score,
                        action_type=self._task,
                        context=f"Ticket: {self._ticket.get('subject', '')}"
                    )
                    base_feedback += f" | AI: {ai_feedback}"
                except Exception as e:
                    logger.debug(f"OpenAI feedback unavailable: {e}")
        except ImportError:
            pass  # OpenAI integration not available
        
        return base_feedback
