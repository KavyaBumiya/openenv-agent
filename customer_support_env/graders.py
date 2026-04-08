"""Unified Grader Classes for OpenEnv Phase 2 Validation

CRITICAL FIX: These graders now use RuleBasedGrader as the single source of truth.
This ensures consistent grading between training (environment.py) and validation (openenv.yaml).

No duplicate grading logic - imports from rule_based_grader.py only.
"""

import logging
from typing import Optional
from .rule_based_grader import RuleBasedGrader
from .data import get_ticket_labels
from .models import TicketAction, TicketObservation

logger = logging.getLogger(__name__)

# EPSILON for strict bounds: scores must be strictly > 0 and strictly < 1
_STRICT_SCORE_EPSILON = 0.001


def _validate_strict_score(score: float, label: str = "score") -> float:
    """Validate and clamp a score to be strictly in (0, 1).
    
    Ensures NO score escapes unclamped - critical for Phase 2 validation.
    """
    if not isinstance(score, (int, float)):
        return _STRICT_SCORE_EPSILON
    
    if score != score or score in (float('inf'), float('-inf')):
        return _STRICT_SCORE_EPSILON
    
    # Clamp to strict bounds, then round
    result = min(1.0 - _STRICT_SCORE_EPSILON, max(_STRICT_SCORE_EPSILON, float(score)))
    result = round(result, 4)
    
    # Hard guard after rounding
    if result <= 0.0 or result >= 1.0:
        return 0.5
    
    return result


class ClassifyGrader:
    """Grade the classify task using unified RuleBasedGrader.
    
    SINGLE SOURCE OF TRUTH: Uses RuleBasedGrader.grade_classify()
    No duplicate logic - ensures consistency with environment.py training.
    """
    
    @staticmethod
    def grade(observation: TicketObservation, action: TicketAction) -> dict:
        """Grade a classify action.
        
        Args:
            observation: TicketObservation with ticket_id and observable fields
            action: TicketAction with predicted category and priority
            
        Returns:
            {
                "score": float (strictly in (0, 1)),
                "category_correct": str ("yes" or "no"),
                "priority_correct": str ("yes" or "no")
            }
        """
        try:
            # Extract ground truth from labels (NOT from observation!)
            ticket_id = observation.ticket_id
            labels = get_ticket_labels(ticket_id)
            
            if not labels:
                logger.error(f"ClassifyGrader: No labels found for ticket {ticket_id}")
                return {"score": 0.5, "category_correct": "no", "priority_correct": "no"}
            
            # Use RuleBasedGrader (single source of truth)
            grader = RuleBasedGrader()
            breakdown = grader.grade_classify(
                predicted_category=(action.category or "general").lower(),
                predicted_priority=(action.priority or "medium").lower(),
                ground_truth_category=labels.get("category", "general"),
                ground_truth_priority=labels.get("priority", "medium"),
                customer_tier=observation.sender_tier,
            )
            
            # Extract results
            score = _validate_strict_score(breakdown.weighted_score, "classify_score")
            category_correct = "yes" if breakdown.category_score.value >= 0.9 else "no"
            priority_correct = "yes" if breakdown.priority_score.value >= 0.9 else "no"
            
            logger.info(f"ClassifyGrader[{ticket_id}]: score={score:.3f}, category={category_correct}, priority={priority_correct}")
            
            return {
                "score": score,
                "category_correct": category_correct,
                "priority_correct": priority_correct,
            }
        
        except Exception as e:
            logger.exception(f"ClassifyGrader error: {e}")
            return {"score": 0.5, "category_correct": "no", "priority_correct": "no"}


class RouteGrader:
    """Grade the route task using unified RuleBasedGrader.
    
    SINGLE SOURCE OF TRUTH: Uses RuleBasedGrader.grade_route()
    No duplicate logic - ensures consistency with environment.py training.
    """
    
    @staticmethod
    def grade(observation: TicketObservation, action: TicketAction) -> dict:
        """Grade a route action.
        
        Args:
            observation: TicketObservation with ticket_id and observable fields
            action: TicketAction with predicted values
            
        Returns:
            {
                "score": float (strictly in (0, 1)),
                "category_correct": str,
                "priority_correct": str,
                "department_correct": str,
                "escalation_correct": str,
            }
        """
        try:
            # Extract ground truth from labels (NOT from observation!)
            ticket_id = observation.ticket_id
            labels = get_ticket_labels(ticket_id)
            
            if not labels:
                logger.error(f"RouteGrader: No labels found for ticket {ticket_id}")
                return {
                    "score": 0.5,
                    "category_correct": "no",
                    "priority_correct": "no",
                    "department_correct": "no",
                    "escalation_correct": "no",
                }
            
            # Prepare inputs
            predicted = {
                "category": (action.category or "general").lower(),
                "priority": (action.priority or "medium").lower(),
                "department": (action.department or "tier1").lower(),
                "requires_escalation": action.requires_escalation or False,
            }
            
            ground_truth = {
                "category": labels.get("category", "general"),
                "priority": labels.get("priority", "medium"),
                "department": labels.get("department", "tier1"),
                "requires_escalation": labels.get("requires_escalation", False),
            }
            
            metadata = {
                "tier": observation.sender_tier,
                "open_since_hours": observation.open_since_hours,
                "sentiment": observation.sentiment,
                "response_keywords": getattr(observation, "response_keywords", []),
            }
            
            # Use RuleBasedGrader (single source of truth)
            grader = RuleBasedGrader()
            breakdown = grader.grade_route(
                predicted=predicted,
                ground_truth=ground_truth,
                ticket_metadata=metadata,
            )
            
            # Extract results
            score = _validate_strict_score(breakdown.weighted_score, "route_score")
            category_correct = "yes" if breakdown.category_score.value >= 0.9 else "no"
            priority_correct = "yes" if breakdown.priority_score.value >= 0.9 else "no"
            department_correct = "yes" if (breakdown.department_score and breakdown.department_score.value >= 0.9) else "no"
            escalation_correct = "yes" if (breakdown.escalation_score and breakdown.escalation_score.value >= 0.9) else "no"
            
            logger.info(f"RouteGrader[{ticket_id}]: score={score:.3f}")
            
            return {
                "score": score,
                "category_correct": category_correct,
                "priority_correct": priority_correct,
                "department_correct": department_correct,
                "escalation_correct": escalation_correct,
            }
        
        except Exception as e:
            logger.exception(f"RouteGrader error: {e}")
            return {
                "score": 0.5,
                "category_correct": "no",
                "priority_correct": "no",
                "department_correct": "no",
                "escalation_correct": "no",
            }


class ResolveGrader:
    """Grade the resolve task using unified RuleBasedGrader.
    
    SINGLE SOURCE OF TRUTH: Uses RuleBasedGrader.grade_resolve()
    No duplicate logic - ensures consistency with environment.py training.
    """
    
    @staticmethod
    def grade(observation: TicketObservation, action: TicketAction) -> dict:
        """Grade a resolve action.
        
        Args:
            observation: TicketObservation with ticket_id and observable fields
            action: TicketAction with predicted values including response
            
        Returns:
            {
                "score": float (strictly in (0, 1)),
                "category_correct": str,
                "priority_correct": str,
                "department_correct": str,
                "escalation_correct": str,
                "response_quality": float,
            }
        """
        try:
            # Extract ground truth from labels (NOT from observation!)
            ticket_id = observation.ticket_id
            labels = get_ticket_labels(ticket_id)
            
            if not labels:
                logger.error(f"ResolveGrader: No labels found for ticket {ticket_id}")
                return {
                    "score": 0.5,
                    "category_correct": "no",
                    "priority_correct": "no",
                    "department_correct": "no",
                    "escalation_correct": "no",
                    "response_quality": 0.5,
                }
            
            # Prepare inputs
            predicted = {
                "category": (action.category or "general").lower(),
                "priority": (action.priority or "medium").lower(),
                "department": (action.department or "tier1").lower(),
                "requires_escalation": action.requires_escalation or False,
                "response": (action.response or "").strip(),
            }
            
            ground_truth = {
                "category": labels.get("category", "general"),
                "priority": labels.get("priority", "medium"),
                "department": labels.get("department", "tier1"),
                "requires_escalation": labels.get("requires_escalation", False),
            }
            
            metadata = {
                "tier": observation.sender_tier,
                "open_since_hours": observation.open_since_hours,
                "sentiment": observation.sentiment,
                "response_keywords": getattr(observation, "response_keywords", []),
            }
            
            # Use RuleBasedGrader (single source of truth)
            grader = RuleBasedGrader()
            breakdown = grader.grade_resolve(
                predicted=predicted,
                ground_truth=ground_truth,
                ticket_metadata=metadata,
            )
            
            # Extract results
            score = _validate_strict_score(breakdown.weighted_score, "resolve_score")
            category_correct = "yes" if breakdown.category_score.value >= 0.9 else "no"
            priority_correct = "yes" if breakdown.priority_score.value >= 0.9 else "no"
            department_correct = "yes" if (breakdown.department_score and breakdown.department_score.value >= 0.9) else "no"
            escalation_correct = "yes" if (breakdown.escalation_score and breakdown.escalation_score.value >= 0.9) else "no"
            response_quality = _validate_strict_score(
                breakdown.response_score.value if breakdown.response_score else 0.5,
                "response_quality"
            )
            
            logger.info(f"ResolveGrader[{ticket_id}]: score={score:.3f}, response_quality={response_quality:.3f}")
            
            return {
                "score": score,
                "category_correct": category_correct,
                "priority_correct": priority_correct,
                "department_correct": department_correct,
                "escalation_correct": escalation_correct,
                "response_quality": response_quality,
            }
        
        except Exception as e:
            logger.exception(f"ResolveGrader error: {e}")
            return {
                "score": 0.5,
                "category_correct": "no",
                "priority_correct": "no",
                "department_correct": "no",
                "escalation_correct": "no",
                "response_quality": 0.5,
            }
