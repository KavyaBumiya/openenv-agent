"""FastAPI server: REST + WebSocket endpoints for the environment."""

import json
import subprocess
import os
import sys
import logging
import uuid
from typing import Optional, Dict, Tuple, Literal
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from ..openenv_compat import create_fastapi_app

from ..environment import CustomerSupportEnvironment
from ..models import TicketAction, TicketObservation

# Configure logging
logger = logging.getLogger(__name__)

# Create base app and register environment routes below.
app = create_fastapi_app(CustomerSupportEnvironment)


# ============= REQUEST/RESPONSE MODELS =============

class ResetRequest(BaseModel):
    task: Literal["classify", "route", "resolve"] = Field(
        "classify",
        description="Task: classify, route, or resolve",
    )
    seed: Optional[int] = Field(None, description="Random seed for reproducibility (0-29)")
    episode_id: Optional[str] = Field(None, description="Optional episode identifier")
    session_id: Optional[str] = Field(None, description="Optional session ID")


class StepRequest(BaseModel):
    session_id: str = Field(..., description="Session ID from /reset response")
    category: Literal["billing", "technical", "account", "shipping", "general"] = Field(
        ...,
        description="Ticket category",
    )
    priority: Literal["low", "medium", "high", "urgent"] = Field(..., description="Priority level")
    department: Optional[Literal["tier1", "tier2", "billing", "engineering", "management"]] = Field(
        None,
        description="Routing department",
    )
    requires_escalation: Optional[bool] = Field(None, description="Escalation flag")
    response: Optional[str] = Field(None, max_length=5000, description="Response text (max 5000 chars)")


# ============= SESSION MANAGEMENT =============
# Store per-session environments to avoid cross-user interference
_sessions: Dict[str, Tuple[CustomerSupportEnvironment, Optional[TicketObservation]]] = {}

def _cleanup_old_sessions(max_sessions: int = 100) -> None:
    """Clean up oldest sessions if limit exceeded."""
    if len(_sessions) > max_sessions:
        # Remove oldest 20% of sessions
        remove_count = max_sessions // 5
        keys_to_remove = list(_sessions.keys())[:remove_count]
        for key in keys_to_remove:
            del _sessions[key]
            logger.debug(f"Cleaned up old session: {key}")



# ============= REQUIRED ENDPOINTS FOR EVALUATION =============

@app.get("/tasks")
async def get_tasks():
    """Return all task definitions for automated evaluation.
    
    The evaluator reads this to determine what to test.
    """
    return [
        {
            "name": "classify",
            "difficulty": "easy",
            "description": "Read a customer support ticket and classify it into a category (billing, technical, account, general, or shipping) and assign a priority level (low, medium, high, urgent).",
            "action_schema": {
                "category": {"type": "string", "enum": ["billing", "technical", "account", "general", "shipping"], "required": True},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "required": True},
            },
        },
        {
            "name": "route",
            "difficulty": "medium",
            "description": "Classify a ticket (category + priority) and route it to the appropriate department: tier1 for simple inquiries, tier2 for complex issues, billing for financial matters, engineering for technical problems, or management for escalations.",
            "action_schema": {
                "category": {"type": "string", "enum": ["billing", "technical", "account", "general", "shipping"], "required": True},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "required": True},
                "department": {"type": "string", "enum": ["tier1", "tier2", "billing", "engineering", "management"], "required": True},
                "requires_escalation": {"type": "boolean", "required": False},
            },
        },
        {
            "name": "resolve",
            "difficulty": "hard",
            "description": "Classify, prioritize, and route a ticket, then draft a professional customer-facing response that acknowledges the issue, provides solutions/timelines, and closes respectfully.",
            "action_schema": {
                "category": {"type": "string", "enum": ["billing", "technical", "account", "general", "shipping"], "required": True},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "required": True},
                "department": {"type": "string", "enum": ["tier1", "tier2", "billing", "engineering", "management"], "required": True},
                "requires_escalation": {"type": "boolean", "required": False},
                "response": {"type": "string", "required": True},
            },
        },
    ]


@app.get("/grader")
async def get_grader():
    """Return scoring philosophy and weight breakdown for all tasks.
    
    This is documentation of the reward function logic.
    """
    return {
        "scoring_philosophy": "Shaped reward signals teach the agent what matters in customer support. Each component is scored separately and combined with task-specific weights.",
        "tasks": {
            "classify": {
                "components": {
                    "category": {
                        "weight": 0.6,
                        "description": "Whether the ticket is correctly categorized (billing, technical, account, general, or shipping). Binary: 1.0 or 0.0. Foundation of correct routing.",
                    },
                    "priority": {
                        "weight": 0.4,
                        "description": "Whether the urgency is correct (low, medium, high, urgent). Graduated: 1.0 exact, 0.6 one step off, 0.2 two steps off, 0.0 three+ steps. Reflects business impact if misclassified.",
                    },
                },
                "total_weight": 1.0,
            },
            "route": {
                "components": {
                    "category": {
                        "weight": 0.35,
                        "description": "Ticket classification (binary). Foundation for routing logic.",
                    },
                    "priority": {
                        "weight": 0.25,
                        "description": "Urgency assessment (graduated). Determines SLA.",
                    },
                    "department": {
                        "weight": 0.25,
                        "description": "Routing destination (binary). Ensures issue reaches correct handler.",
                    },
                    "escalation": {
                        "weight": 0.15,
                        "description": "Escalation judgment (binary). Tests whether agent recognizes high-severity cases requiring supervisor review.",
                    },
                },
                "total_weight": 1.0,
            },
            "resolve": {
                "components": {
                    "category": {
                        "weight": 0.2,
                        "description": "Ticket classification (binary). Foundation for response context.",
                    },
                    "priority": {
                        "weight": 0.15,
                        "description": "Urgency assessment (graduated). Determines response tone and timeline.",
                    },
                    "department": {
                        "weight": 0.2,
                        "description": "Routing destination (binary). Ensures specialized expertise in response.",
                    },
                    "escalation": {
                        "weight": 0.15,
                        "description": "Escalation judgment (binary). Recognizes when supervisor sign-off needed.",
                    },
                    "response": {
                        "weight": 0.3,
                        "description": "Response quality (graduated by keyword presence + sentiment matching). Important because this is the visible customer-facing output that impacts CSAT.",
                    },
                },
                "total_weight": 1.0,
            },
        },
        "response_grading_criteria": {
            "method": "Keyword presence",
            "logic": "Response must contain at least 75% of required keywords (minimum 3). Scoring: all keywords=1.0, most=0.6, half=0.3, few=0.0. Keywords represent essential response elements: acknowledgment, solution/timeline, professional tone.",
        },
    }


@app.post("/baseline")
async def run_baseline():
    """Execute baseline.py and return scores per task.
    
    Proof that the environment is usable and produces meaningful variance.
    This endpoint is called during evaluation.
    
    Requires GROQ_API_KEY in environment.
    """
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(
            status_code=400,
            detail="GROQ_API_KEY not set in environment. Baseline cannot run."
        )
    
    try:
        # Run baseline.py in subprocess
        # Change to project directory to ensure imports work
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        result = subprocess.run(
            [sys.executable, "-m", "customer_support_env.baseline"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=project_root,
        )
        
        if result.returncode != 0:
            return {
                "status": "failed",
                "error": result.stderr,
                "stdout": result.stdout,
            }
        
        # Extract JSON from output (baseline.py may print logs before JSON)
        # Try to parse entire output first, then fall back to extracting JSON
        output_text = result.stdout.strip()
        
        try:
            # Try direct JSON parse first
            output = json.loads(output_text)
            return {
                "status": "success",
                "results": output,
            }
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from output
            # Look for the last JSON object delimited by { }
            import re
            
            # Find all potential JSON objects (strings starting with { and ending with })
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, output_text)
            
            if matches:
                # Take the last (likely most complete) JSON object
                last_json_str = matches[-1]
                try:
                    output = json.loads(last_json_str)
                    return {
                        "status": "success",
                        "results": output,
                    }
                except json.JSONDecodeError:
                    pass
            
            # If JSON extraction failed, return raw output
            return {
                "status": "completed_but_unparseable",
                "output": output_text,
                "note": "Baseline completed but couldn't parse JSON from output. Check logs above.",
            }
    
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "error": "Baseline script exceeded 5 minute timeout",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


# ============= STANDARD OPENENV REST ENDPOINTS =============

@app.post("/reset")
async def reset(req: ResetRequest):
    """Reset environment for new episode.
    
    Args:
        task: Task type (classify, route, resolve). Defaults to "classify".
        seed: Random seed for reproducibility (0-29). If None, uses random.
        episode_id: Optional episode identifier for logging.
        session_id: Optional session ID. If not provided, generates new one.
    
    Returns:
        {
            "session_id": "...",
            "observation": {...ticket fields...}
        }
    """
    try:
        # Create or reuse session
        session_id = req.session_id or str(uuid.uuid4())
        
        # Create new environment for this session
        env = CustomerSupportEnvironment()
        obs = env.reset(task=req.task, seed=req.seed, episode_id=req.episode_id)
        
        # Store in session map
        _sessions[session_id] = (env, obs)
        
        # Cleanup if too many sessions
        _cleanup_old_sessions()
        
        logger.info(f"Reset session {session_id}: task={req.task}, seed={req.seed}")
        
        # Return observation with session ID
        return {
            "session_id": session_id,
            "observation": obs.model_dump()
        }
    except ValueError as e:
        logger.warning(f"Validation error in /reset: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in /reset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/step")
async def step(req: StepRequest):
    """Submit action and receive reward.
    
    Args:
        session_id: Session ID from /reset response (required)
        category: Ticket classification (billing, technical, account, general, shipping)
        priority: Urgency level (low, medium, high, urgent)
        department: Routing destination (tier1, tier2, billing, engineering, management)
        requires_escalation: Whether to flag for supervisor review (boolean)
        response: Customer-facing response text (required for resolve task, max 5000 chars)
    
    Returns:
        {
            "observation": {...ticket fields...},
            "reward": float,
            "done": bool
        }
    """
    # Validate session exists
    if req.session_id not in _sessions:
        logger.warning(f"Step request for invalid session: {req.session_id}")
        raise HTTPException(status_code=404, detail=f"Session not found: {req.session_id}")
    
    try:
        env, obs = _sessions[req.session_id]
        
        # Validate response length
        if req.response and len(req.response) > 5000:
            raise ValueError("Response exceeds maximum length of 5000 characters")
        
        # Create action
        action = TicketAction(
            category=req.category,
            priority=req.priority,
            department=req.department,
            requires_escalation=req.requires_escalation,
            response=req.response,
        )
        
        # Step environment
        obs = env.step(action)
        obs_dict = obs.model_dump()
        
        # Extract reward and done from observation (included in single-turn design)
        reward = obs_dict.pop("reward", 0.0)
        done = obs_dict.pop("done", True)
        
        # Update session
        _sessions[req.session_id] = (env, obs)
        
        logger.debug(f"Step session {req.session_id}: reward={reward:.3f}")
        
        # Return nested structure: observation separate from reward/done
        return {
            "observation": obs_dict,
            "reward": reward,
            "done": done,
        }
    except ValueError as e:
        logger.warning(f"Validation error in /step for session {req.session_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in /step for session {req.session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state")
async def state(session_id: str = Query(..., description="Session ID from /reset response")):
    """Get current environment state for a session.
    
    Args:
       session_id: Session ID from /reset response
    
    Returns:
        TicketState with current ticket, task, step count, etc.
        Also includes current_ticket_id for debugging seed-based reproducibility.
    """
    if session_id not in _sessions:
        logger.warning(f"State request for invalid session: {session_id}")
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    
    try:
        env, obs = _sessions[session_id]
        state_dict = env.state.model_dump()
        # Add the current ticket ID so agents can verify which ticket is active
        if env._ticket is not None:
            state_dict["current_ticket_id"] = env._ticket["id"]
        return state_dict
    except Exception as e:
        logger.error(f"Error getting state for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Health check and API info."""
    return {
        "name": "Customer Support RL Environment",
        "version": "0.1.0",
        "endpoints": {
            "/docs": "Interactive API documentation (Swagger UI)",
            "/tasks": "GET - Task definitions for evaluation",
            "/grader": "GET - Scoring philosophy and reward breakdown",
            "/baseline": "POST - Run baseline evaluation with Groq",
            "/ws": "WebSocket - Real-time agent interaction",
            "/reset": "POST - Reset environment for new episode",
            "/step": "POST - Submit action and get reward",
            "/state": "GET - Get current environment state",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint. Returns 200 when the server is ready."""
    return {
        "status": "ok",
        "environment": "CustomerSupportEnvironment",
        "version": "0.1.0",
        "tasks": ["classify", "route", "resolve"],
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time agent interaction.
    
    Protocol:
      1. Client sends: {"action": "reset", "task": "classify", "seed": 0}
      2. Server responds: observation dict
      3. Client sends: {"action": "step", "category": "...", "priority": "..."}
      4. Server responds: {"observation": {...}, "reward": ..., "done": ...}
    """
    await websocket.accept()
    ws_env = CustomerSupportEnvironment()  # Each WebSocket gets its own env
    
    try:
        while True:
            data = await websocket.receive_json()
            action_type = data.get("action")
            
            if action_type == "reset":
                obs = ws_env.reset(
                    task=data.get("task", "classify"),
                    seed=data.get("seed"),
                    episode_id=data.get("episode_id")
                )
                await websocket.send_json(obs.model_dump())
            
            elif action_type == "step":
                ticket_action = TicketAction(
                    category=data.get("category", ""),
                    priority=data.get("priority", ""),
                    department=data.get("department"),
                    requires_escalation=data.get("requires_escalation"),
                    response=data.get("response")
                )
                obs = ws_env.step(ticket_action)
                obs_dict = obs.model_dump()
                
                # Extract reward and done from observation
                reward = obs_dict.pop("reward", 0.0)
                done = obs_dict.pop("done", True)
                
                # Send nested structure matching /step endpoint
                await websocket.send_json({
                    "observation": obs_dict,
                    "reward": reward,
                    "done": done,
                })
            
            else:
                await websocket.send_json({"error": f"Unknown action: {action_type}"})
    
    except WebSocketDisconnect:
        pass  # Client disconnected normally
