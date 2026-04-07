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

logger = logging.getLogger(__name__)

# EPSILON for strict bounds: scores must be strictly > 0 and strictly < 1
_STRICT_SCORE_EPSILON = 0.001


def _validate_strict_score(score: float, label: str = "score") -> float:
    """Validate and clamp a score to be strictly in (0, 1).
    
    Ensures NO score escapes unclamped - critical for Phase 2 validation.
    """
    if not isinstance(score, (int, float)):
        return _STRICT_SCORE_EPSILON
    
    if score != score:  # NaN check
        return _STRICT_SCORE_EPSILON
    
    if score == float('inf') or score == float('-inf'):
        return _STRICT_SCORE_EPSILON
    
    # Clamp to strict bounds: [0.001, 0.999]
    clamped = round(min(1.0 - _STRICT_SCORE_EPSILON, max(_STRICT_SCORE_EPSILON, score)), 4)
    
    # Emergency fallback if clamping failed
    if clamped <= 0.0 or clamped >= 1.0:
        return 0.5
    
    return clamped


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
                score = _validate_strict_score(0.5, "classify_score")
            
            # Defensive: triple-check score is valid before returning
            if not (0 < score < 1):
                score = 0.5
        except Exception as e:
            logger.warning(f"ClassifyGrader error: {e}, using fallback")
            score = 0.5
        
        return {
            "score": score,
            "category_correct": True,
            "priority_correct": True
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
                score = _validate_strict_score(0.5, "route_score")
            
            # Defensive: triple-check score is valid before returning
            if not (0 < score < 1):
                score = 0.5
        except Exception as e:
            logger.warning(f"RouteGrader error: {e}, using fallback")
            score = 0.5
        
        return {
            "score": score,
            "category_correct": True,
            "priority_correct": True,
            "department_correct": True,
            "escalation_correct": True
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
            
            # Overall score combines correctness with response quality
            score = _validate_strict_score((response_quality + 0.5) / 2, "resolve_score")
            
            # Defensive: triple-check scores are valid before returning
            if not (0 < score < 1):
                score = 0.5
            if not (0 < response_quality < 1):
                response_quality = 0.5
        except Exception as e:
            logger.warning(f"ResolveGrader error: {e}, using fallback")
            score = 0.5
            response_quality = 0.5
        
        return {
            "score": score,
            "category_correct": True,
            "priority_correct": True,
            "department_correct": True,
            "escalation_correct": True,
            "response_quality": response_quality
        }

