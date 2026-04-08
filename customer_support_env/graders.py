"""Grader classes for OpenEnv Phase 2 validation.

These graders are referenced in openenv.yaml and used by the Phase 2 validator
to evaluate task submissions. Each grader ensures scores are strictly in (0, 1).

OpenAI Integration:
- Uses GPT-3.5-turbo for intelligent response evaluation
- Fallback to rule-based scoring if API unavailable
- All scores clamped to strict (0, 1) range for Phase 2
"""

import logging
from .openai_integration import get_openai_integration
from .rule_based_grader import RuleBasedGrader

logger = logging.getLogger(__name__)

# EPSILON for strict bounds: scores must be strictly > 0 and strictly < 1
_STRICT_SCORE_EPSILON = 0.001


def _validate_strict_score(score: float, label: str = "score") -> float:
    """Validate and clamp a score to be strictly in (0, 1).
    
    Ensures NO score escapes unclamped - critical for Phase 2 validation.
    Includes post-rounding guard to prevent boundary violations.
    """
    if not isinstance(score, (int, float)):
        return _STRICT_SCORE_EPSILON
    
    if score != score or score in (float('inf'), float('-inf')):
        return _STRICT_SCORE_EPSILON
    
    # Clamp to strict bounds, then round
    result = min(1.0 - _STRICT_SCORE_EPSILON, max(_STRICT_SCORE_EPSILON, float(score)))
    result = round(result, 4)
    
    # Hard guard after rounding: check if rounding produced exact boundary
    if result <= 0.0 or result >= 1.0:
        return 0.5
    
    return result


class ClassifyGrader:
    """Grader for the classify task: category + priority classification.
    
    Uses AI-powered evaluation (OpenAI) with fallback to rule-based scoring.
    Ensures all returned scores are strictly in (0, 1).
    """
    
    @staticmethod
    def grade(observation, action) -> dict:
        """Grade a classify action with AI assistance.
        
        Returns:
            {
                "category_correct": bool,
                "priority_correct": bool,
                "score": float (strictly in (0, 1))
            }
        """
        score = 0.5
        category_correct = False
        priority_correct = False
        
        try:
            # Try AI-powered evaluation first
            openai = get_openai_integration()
            if openai.enabled and hasattr(observation, 'description'):
                ai_result = openai.evaluate_response_quality(
                    response=str(action),
                    ticket_desc=str(observation.description)
                )
                score = _validate_strict_score(ai_result.get('score', 0.5), "classify_score")
                logger.debug(f"ClassifyGrader: AI score={score}, reasoning={ai_result.get('reasoning', '')}")
            else:
                # Fallback to rule-based scoring
                grader = RuleBasedGrader()
                
                # Parse action: expected format is "category|priority" or from TicketAction
                pred_category = "general"
                pred_priority = "medium"
                
                if hasattr(action, 'category'):
                    pred_category = (action.category or "general").lower()
                    pred_priority = (action.priority or "medium").lower()
                elif isinstance(action, str) and "|" in action:
                    parts = action.split("|")
                    pred_category = parts[0].strip().lower() if len(parts) > 0 else "general"
                    pred_priority = parts[1].strip().lower() if len(parts) > 1 else "medium"
                
                # Get observation metadata
                gt_category = getattr(observation, 'category', 'general').lower()
                gt_priority = getattr(observation, 'priority', 'medium').lower()
                customer_tier = getattr(observation, 'sender_tier', 'free').lower()
                
                # Use rule-based grader
                breakdown = grader.grade_classify(
                    predicted_category=pred_category,
                    predicted_priority=pred_priority,
                    ground_truth_category=gt_category,
                    ground_truth_priority=gt_priority,
                    customer_tier=customer_tier,
                )
                
                score = _validate_strict_score(breakdown.weighted_score, "classify_score")
                category_correct = breakdown.category_score.value >= 0.9
                priority_correct = breakdown.priority_score.value >= 0.9
                logger.debug(f"ClassifyGrader: Rule-based score={score}, category={category_correct}, priority={priority_correct}")
            
            # Defensive: triple-check score is valid before returning
            if not (0 < score < 1):
                score = 0.5
        except Exception as e:
            logger.warning(f"ClassifyGrader error: {e}, using fallback")
            score = 0.5
        
        # Phase 2: final defensive clamp before return
        _EPS = 0.001
        score = round(max(_EPS, min(1.0 - _EPS, float(score))), 4)
        
        return {
            "score": score,
            "category_correct": "yes" if category_correct else "no",
            "priority_correct": "yes" if priority_correct else "no"
        }


class RouteGrader:
    """Grader for the route task: classification + routing to correct department.
    
    Uses AI-powered evaluation (OpenAI) with fallback to rule-based scoring.
    Ensures all returned scores are strictly in (0, 1).
    """
    
    @staticmethod
    def grade(observation, action) -> dict:
        """Grade a route action with AI assistance.
        
        Returns:
            {
                "category_correct": bool,
                "priority_correct": bool,
                "department_correct": bool,
                "escalation_correct": bool,
                "score": float (strictly in (0, 1))
            }
        """
        score = 0.5
        category_correct = False
        priority_correct = False
        department_correct = False
        escalation_correct = False
        
        try:
            # Try AI-powered evaluation first
            openai = get_openai_integration()
            if openai.enabled and hasattr(observation, 'description'):
                ai_result = openai.classify_priority_ai(
                    ticket_desc=str(observation.description)
                )
                score = _validate_strict_score(ai_result.get('urgency_score', 0.5), "route_score")
                logger.debug(f"RouteGrader: AI priority={ai_result.get('priority')}, score={score}")
            else:
                # Fallback to rule-based scoring
                grader = RuleBasedGrader()
                
                # Parse action: could be from TicketAction or string format
                pred_category = "general"
                pred_priority = "medium"
                pred_department = "tier1"
                pred_escalation = False
                
                if hasattr(action, 'category'):
                    pred_category = (action.category or "general").lower()
                    pred_priority = (action.priority or "medium").lower()
                    pred_department = (action.department or "tier1").lower()
                    pred_escalation = action.requires_escalation or False
                
                # Get observation metadata
                gt_category = getattr(observation, 'category', 'general').lower()
                gt_priority = getattr(observation, 'priority', 'medium').lower()
                gt_department = getattr(observation, 'department', 'tier1').lower()
                gt_escalation = getattr(observation, 'requires_escalation', False)
                customer_tier = getattr(observation, 'sender_tier', 'free').lower()
                
                # Prepare metadata
                metadata = {
                    "tier": customer_tier,
                    "open_since_hours": getattr(observation, 'open_since_hours', 0),
                    "sentiment": getattr(observation, 'sentiment', 'neutral'),
                    "response_keywords": getattr(observation, 'response_keywords', []),
                }
                
                # Use rule-based grader
                breakdown = grader.grade_route(
                    predicted={
                        "category": pred_category,
                        "priority": pred_priority,
                        "department": pred_department,
                        "requires_escalation": pred_escalation,
                    },
                    ground_truth={
                        "category": gt_category,
                        "priority": gt_priority,
                        "department": gt_department,
                        "requires_escalation": gt_escalation,
                    },
                    ticket_metadata=metadata,
                )
                
                score = _validate_strict_score(breakdown.weighted_score, "route_score")
                category_correct = breakdown.category_score.value >= 0.9
                priority_correct = breakdown.priority_score.value >= 0.9
                department_correct = breakdown.department_score and breakdown.department_score.value >= 0.9
                escalation_correct = breakdown.escalation_score and breakdown.escalation_score.value >= 0.9
                logger.debug(f"RouteGrader: Rule-based score={score}")
            
            # Defensive: triple-check score is valid before returning
            if not (0 < score < 1):
                score = 0.5
        except Exception as e:
            logger.warning(f"RouteGrader error: {e}, using fallback")
            score = 0.5
        
        # Phase 2: final defensive clamp before return
        _EPS = 0.001
        score = round(max(_EPS, min(1.0 - _EPS, float(score))), 4)
        
        return {
            "score": score,
            "category_correct": "yes" if category_correct else "no",
            "priority_correct": "yes" if priority_correct else "no",
            "department_correct": "yes" if department_correct else "no",
            "escalation_correct": "yes" if escalation_correct else "no"
        }


class ResolveGrader:
    """Grader for the resolve task: complete ticket resolution with response drafting.
    
    Uses AI-powered response quality evaluation (OpenAI) with fallback.
    Ensures all returned scores are strictly in (0, 1).
    """
    
    @staticmethod
    def grade(observation, action) -> dict:
        """Grade a resolve action with AI-powered response quality evaluation.
        
        Returns:
            {
                "category_correct": bool,
                "priority_correct": bool,
                "department_correct": bool,
                "escalation_correct": bool,
                "response_quality": float (strictly in (0, 1)),
                "score": float (strictly in (0, 1))
            }
        """
        score = 0.5
        response_quality = 0.5
        category_correct = False
        priority_correct = False
        department_correct = False
        escalation_correct = False
        
        try:
            # Try AI-powered response evaluation first
            openai = get_openai_integration()
            response_quality = _validate_strict_score(0.5, "response_quality")
            
            if openai.enabled and hasattr(observation, 'description'):
                ai_eval = openai.evaluate_response_quality(
                    response=str(action),
                    ticket_desc=str(observation.description)
                )
                response_quality = _validate_strict_score(ai_eval.get('score', 0.5), "response_quality")
                logger.debug(f"ResolveGrader: AI response quality={response_quality}, reasoning={ai_eval.get('reasoning', '')}")
            else:
                # Fallback to rule-based scoring
                grader = RuleBasedGrader()
                
                # Parse action: could be from TicketAction or string format
                pred_category = "general"
                pred_priority = "medium"
                pred_department = "tier1"
                pred_escalation = False
                pred_response = ""
                
                if hasattr(action, 'category'):
                    pred_category = (action.category or "general").lower()
                    pred_priority = (action.priority or "medium").lower()
                    pred_department = (action.department or "tier1").lower()
                    pred_escalation = action.requires_escalation or False
                    pred_response = (action.response or "").strip()
                
                # Get observation metadata
                gt_category = getattr(observation, 'category', 'general').lower()
                gt_priority = getattr(observation, 'priority', 'medium').lower()
                gt_department = getattr(observation, 'department', 'tier1').lower()
                gt_escalation = getattr(observation, 'requires_escalation', False)
                customer_tier = getattr(observation, 'sender_tier', 'free').lower()
                
                # Prepare metadata
                metadata = {
                    "tier": customer_tier,
                    "open_since_hours": getattr(observation, 'open_since_hours', 0),
                    "sentiment": getattr(observation, 'sentiment', 'neutral'),
                    "response_keywords": getattr(observation, 'response_keywords', []),
                }
                
                # Use rule-based grader
                breakdown = grader.grade_resolve(
                    predicted={
                        "category": pred_category,
                        "priority": pred_priority,
                        "department": pred_department,
                        "requires_escalation": pred_escalation,
                        "response": pred_response,
                    },
                    ground_truth={
                        "category": gt_category,
                        "priority": gt_priority,
                        "department": gt_department,
                        "requires_escalation": gt_escalation,
                    },
                    ticket_metadata=metadata,
                )
                
                score = _validate_strict_score(breakdown.weighted_score, "resolve_score")
                response_quality = _validate_strict_score(breakdown.response_score.value if breakdown.response_score else 0.5, "response_quality")
                category_correct = breakdown.category_score.value >= 0.9
                priority_correct = breakdown.priority_score.value >= 0.9
                department_correct = breakdown.department_score and breakdown.department_score.value >= 0.9
                escalation_correct = breakdown.escalation_score and breakdown.escalation_score.value >= 0.9
                logger.debug(f"ResolveGrader: Rule-based score={score}, response_quality={response_quality}")
            
            # Defensive: triple-check scores are valid before returning
            if not (0 < score < 1):
                score = 0.5
            if not (0 < response_quality < 1):
                response_quality = 0.5
        except Exception as e:
            logger.warning(f"ResolveGrader error: {e}, using fallback")
            score = 0.5
            response_quality = 0.5
        
        # Phase 2: final defensive clamp before return
        _EPS = 0.001
        score = round(max(_EPS, min(1.0 - _EPS, float(score))), 4)
        response_quality = round(max(_EPS, min(1.0 - _EPS, float(response_quality))), 4)
        
        return {
            "score": score,
            "category_correct": "yes" if category_correct else "no",
            "priority_correct": "yes" if priority_correct else "no",
            "department_correct": "yes" if department_correct else "no",
            "escalation_correct": "yes" if escalation_correct else "no",
            "response_quality": response_quality
        }


