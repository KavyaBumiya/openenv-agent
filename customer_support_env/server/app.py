"""FastAPI server: REST + WebSocket endpoints for the environment."""

import json
import subprocess
import os
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from ..openenv_compat import create_fastapi_app

from ..environment import CustomerSupportEnvironment
from ..models import TicketAction


# Create base app with standard endpoints (/ws, /reset, /step, /state, /health)
app = create_fastapi_app(CustomerSupportEnvironment)


# ============= REQUEST/RESPONSE MODELS =============

class ResetRequest(BaseModel):
    task: str = "classify"
    seed: Optional[int] = None
    episode_id: Optional[str] = None


class StepRequest(BaseModel):
    category: str
    priority: str
    department: Optional[str] = None
    requires_escalation: Optional[bool] = None
    response: Optional[str] = None


# Global environment instance for REST endpoints
_env = CustomerSupportEnvironment()



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
                        "weight": 0.15,
                        "description": "Routing destination (binary). Ensures specialized expertise in response.",
                    },
                    "escalation": {
                        "weight": 0.1,
                        "description": "Escalation judgment (binary). Recognizes when supervisor sign-off needed.",
                    },
                    "response": {
                        "weight": 0.4,
                        "description": "Response quality (graduated by keyword presence + sentiment matching). Highest weight because this is the visible customer-facing output that impacts CSAT.",
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
        result = subprocess.run(
            ["python", "-m", "customer_support_env.baseline"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        
        if result.returncode != 0:
            return {
                "status": "failed",
                "error": result.stderr,
                "stdout": result.stdout,
            }
        
        # Parse output (baseline.py should output JSON)
        try:
            output = json.loads(result.stdout)
            return {
                "status": "success",
                "results": output,
            }
        except json.JSONDecodeError:
            return {
                "status": "completed",
                "output": result.stdout,
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
    
    Returns:
        TicketObservation with subject, body, tier, task info.
    """
    try:
        obs = _env.reset(task=req.task, seed=req.seed, episode_id=req.episode_id)
        return obs.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step")
async def step(req: StepRequest):
    """Submit action and receive reward.
    
    Args:
        category: Ticket classification (billing, technical, account, general, shipping)
        priority: Urgency level (low, medium, high, urgent)
        department: Routing destination (tier1, tier2, billing, engineering, management)
        requires_escalation: Whether to flag for supervisor review (boolean)
        response: Customer-facing response text (required for resolve task)
    
    Returns:
        TicketObservation with reward, feedback, done flag.
    """
    try:
        action = TicketAction(
            category=req.category,
            priority=req.priority,
            department=req.department,
            requires_escalation=req.requires_escalation,
            response=req.response,
        )
        obs = _env.step(action)
        return obs.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
async def state():
    """Get current environment state.
    
    Returns:
        TicketState with current ticket, task, step count, etc.
        Also includes current_ticket_id for debugging seed-based reproducibility.
    """
    try:
        state_dict = _env.state.model_dump()
        # Add the current ticket ID so agents can verify which ticket is active
        if _env._ticket is not None:
            state_dict["current_ticket_id"] = _env._ticket["id"]
        return state_dict
    except AttributeError:
        raise HTTPException(status_code=400, detail="Environment not initialized. Call /reset first.")

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
      4. Server responds: observation dict with reward and done=True
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
                await websocket.send_json(obs.model_dump())
            
            else:
                await websocket.send_json({"error": f"Unknown action: {action_type}"})
    
    except WebSocketDisconnect:
        pass  # Client disconnected normally
