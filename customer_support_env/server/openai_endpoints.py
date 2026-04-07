"""
OpenAI-powered API endpoints for intelligent feedback and analysis.

Endpoints:
- POST /ai/evaluate-response - Evaluate response quality using AI
- POST /ai/get-feedback - Get AI-generated constructive feedback  
- GET /ai/analyze-strategy - Analyze agent strategy over episodes
- POST /ai/classify-priority - AI-powered priority classification
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Create a router for AI endpoints
router = APIRouter(prefix="/ai", tags=["OpenAI"])


class EvaluateResponseRequest(BaseModel):
    response: str
    ticket_description: str


class FeedbackRequest(BaseModel):
    score: float
    action_type: str  # 'classify', 'route', 'resolve'
    context: str


class ClassifyPriorityRequest(BaseModel):
    ticket_description: str


class AnalyzeStrategyRequest(BaseModel):
    actions: list
    tickets_processed: int


@router.post("/evaluate-response")
async def evaluate_response(req: EvaluateResponseRequest):
    """
    Evaluate customer support response quality using AI.
    
    Args:
        response: The support agent's response text
        ticket_description: Original ticket description
        
    Returns:
        {
            "score": float (0-1),
            "reasoning": str,
            "suggestions": list[str]
        }
    """
    try:
        from ..openai_integration import get_openai_integration
        
        openai = get_openai_integration()
        result = openai.evaluate_response_quality(
            response=req.response,
            ticket_desc=req.ticket_description
        )
        return result
        
    except Exception as e:
        logger.error(f"Response evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get-feedback")
async def get_feedback(req: FeedbackRequest):
    """
    Generate intelligent constructive feedback for agent actions.
    
    Args:
        score: The reward/score received (0-1)
        action_type: Type of action ('classify', 'route', 'resolve')
        context: Context about the action
        
    Returns:
        {"feedback": str}
    """
    try:
        from ..openai_integration import get_openai_integration
        
        openai = get_openai_integration()
        feedback = openai.generate_feedback(
            score=req.score,
            action_type=req.action_type,
            context=req.context
        )
        return {"feedback": feedback}
        
    except Exception as e:
        logger.error(f"Feedback generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify-priority")
async def classify_priority(req: ClassifyPriorityRequest):
    """
    Use AI to classify ticket priority (complements rule-based scoring).
    
    Args:
        ticket_description: Ticket description and context
        
    Returns:
        {
            "priority": str ('low', 'medium', 'high'),
            "urgency_score": float (0-1),
            "reasoning": str
        }
    """
    try:
        from ..openai_integration import get_openai_integration
        
        openai = get_openai_integration()
        result = openai.classify_priority_ai(
            ticket_desc=req.ticket_description
        )
        return result
        
    except Exception as e:
        logger.error(f"Priority classification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-strategy")
async def analyze_strategy(req: AnalyzeStrategyRequest):
    """
    Analyze agent's overall strategy and performance using AI.
    
    Args:
        actions: List of actions taken
        tickets_processed: Number of tickets processed
        
    Returns:
        {
            "performance_level": str,
            "strengths": list[str],
            "weaknesses": list[str]
        }
    """
    try:
        from ..openai_integration import get_openai_integration
        
        openai = get_openai_integration()
        analysis = openai.analyze_agent_strategy(
            actions=req.actions,
            tickets=[{"id": f"TKT-{i:03d}"} for i in range(req.tickets_processed)]
        )
        return analysis
        
    except Exception as e:
        logger.error(f"Strategy analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def ai_status():
    """
    Check OpenAI integration status.
    
    Returns:
        {"enabled": bool, "message": str}
    """
    try:
        from ..openai_integration import get_openai_integration
        
        openai = get_openai_integration()
        status = {
            "enabled": openai.enabled,
            "message": "OpenAI integration is active" if openai.enabled else "OpenAI integration is disabled"
        }
        return status
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "enabled": False,
            "message": f"Error checking status: {str(e)}"
        }
