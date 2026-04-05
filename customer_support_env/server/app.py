"""
customer_support_env/server/app.py
──────────────────────────────────
FastAPI server exposing the OpenEnv REST interface.

Endpoints:
  GET  /health        Health check (required by HF Spaces)
  GET  /tasks         Task definitions
  GET  /grader        Reward-function documentation
  POST /reset         Start episode, returns observation + session_id
    POST /step          Submit action, returns observation + reward + done + info
  GET  /state         Read current episode state
  WS   /ws            WebSocket for real-time interaction
"""

from __future__ import annotations

import logging
import uuid
from typing import Dict, Literal, Optional, Tuple

from fastapi import Body, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..environment import CustomerSupportEnvironment
from ..models import TicketAction, TicketObservation

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Customer Support RL Environment",
    description="OpenEnv-compliant customer-support ticket triage environment.",
    version="0.1.0",
)

# ─────────────────────────────────────────────────────────────────────────────
# Session store  (in-memory; scoped per container instance)
# ─────────────────────────────────────────────────────────────────────────────

_sessions: Dict[str, Tuple[CustomerSupportEnvironment, Optional[TicketObservation]]] = {}

_MAX_SESSIONS = 200


def _evict_old_sessions() -> None:
    if len(_sessions) > _MAX_SESSIONS:
        to_remove = list(_sessions.keys())[: _MAX_SESSIONS // 5]
        for k in to_remove:
            del _sessions[k]

# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    task: Literal["classify", "route", "resolve"] = "classify"
    seed: Optional[int] = None
    episode_id: Optional[str] = None
    session_id: Optional[str] = None


class StepRequest(BaseModel):
    session_id: str
    category: Literal["billing", "technical", "account", "shipping", "general"]
    priority: Literal["low", "medium", "high", "urgent"]
    department: Optional[Literal["tier1", "tier2", "billing", "engineering", "management"]] = None
    requires_escalation: Optional[bool] = None
    response: Optional[str] = Field(None, max_length=5000)

# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "customer_support_env",
        "docs": "/docs",
        "tasks": "/tasks",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/tasks")
async def get_tasks():
    return [
        {
            "name": "classify",
            "difficulty": "easy",
            "description": (
                "Read a customer support ticket and classify it into a category "
                "(billing, technical, account, general, or shipping) and assign a priority "
                "(low, medium, high, urgent)."
            ),
            "action_schema": {
                "category": {"type": "string", "enum": ["billing", "technical", "account", "general", "shipping"], "required": True},
                "priority":  {"type": "string", "enum": ["low", "medium", "high", "urgent"], "required": True},
            },
        },
        {
            "name": "route",
            "difficulty": "medium",
            "description": (
                "Classify a ticket and route it to the correct department "
                "(tier1, tier2, billing, engineering, management) with an optional escalation flag."
            ),
            "action_schema": {
                "category":            {"type": "string", "enum": ["billing", "technical", "account", "general", "shipping"], "required": True},
                "priority":            {"type": "string", "enum": ["low", "medium", "high", "urgent"], "required": True},
                "department":          {"type": "string", "enum": ["tier1", "tier2", "billing", "engineering", "management"], "required": True},
                "requires_escalation": {"type": "boolean", "required": False},
            },
        },
        {
            "name": "resolve",
            "difficulty": "hard",
            "description": (
                "Classify, prioritize, and route a ticket, then draft a professional "
                "customer-facing response that acknowledges the issue and provides next steps."
            ),
            "action_schema": {
                "category":            {"type": "string", "enum": ["billing", "technical", "account", "general", "shipping"], "required": True},
                "priority":            {"type": "string", "enum": ["low", "medium", "high", "urgent"], "required": True},
                "department":          {"type": "string", "enum": ["tier1", "tier2", "billing", "engineering", "management"], "required": True},
                "requires_escalation": {"type": "boolean", "required": False},
                "response":            {"type": "string", "required": True},
            },
        },
    ]


@app.get("/grader")
async def get_grader():
    return {
        "type": "shaped",
        "range": [0.0, 1.0],
        "tasks": {
            "classify": {
                "weights": {"category": 0.6, "priority": 0.4},
                "notes": {
                    "category": "Binary — exact match only.",
                    "priority": "Graduated — 1.0 exact, 0.6 one step off, 0.2 two steps off.",
                },
            },
            "route": {
                "weights": {"category": 0.35, "priority": 0.25, "department": 0.25, "escalation": 0.15},
                "notes": {
                    "department": "Partial credit (0.4) for tier1→tier2 or tier2↔engineering.",
                    "escalation": "Binary.",
                },
            },
            "resolve": {
                "weights": {"category": 0.2, "priority": 0.15, "department": 0.2, "escalation": 0.15, "response": 0.3},
                "notes": {
                    "response": (
                        "Keyword coverage (at least half, with minimum 3 when applicable). "
                        "+0.1 empathy bonus for frustrated customers. "
                        "-0.1 if no actionable next-step phrases."
                    ),
                },
            },
        },
    }


@app.post("/reset")
async def reset(req: Optional[ResetRequest] = Body(None)):
    try:
        if req is None:
            req = ResetRequest()
        session_id = req.session_id or str(uuid.uuid4())
        env = CustomerSupportEnvironment()
        obs = env.reset(task=req.task, seed=req.seed, episode_id=req.episode_id)
        _sessions[session_id] = (env, obs)
        _evict_old_sessions()
        logger.info("reset session=%s task=%s seed=%s", session_id, req.task, req.seed)
        return {"session_id": session_id, "observation": obs.model_dump()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("reset failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/step")
async def step(req: StepRequest):
    if req.session_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"Session not found: {req.session_id}")
    try:
        env, _ = _sessions[req.session_id]
        action = TicketAction(
            category=req.category,
            priority=req.priority,
            department=req.department,
            requires_escalation=req.requires_escalation,
            response=req.response,
        )
        obs, reward, done, info = env.step(action)
        obs_dict = obs.model_dump()
        obs_dict.pop("reward", None)
        obs_dict.pop("done", None)
        _sessions[req.session_id] = (env, obs)
        logger.debug("step session=%s reward=%.3f", req.session_id, reward)
        return {"observation": obs_dict, "reward": reward, "done": done, "info": info}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("step failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/state")
async def get_state(session_id: str = Query(...)):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    try:
        env, _ = _sessions[session_id]
        return env.state().model_dump()
    except Exception as exc:
        logger.exception("state failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket  (optional — for real-time agent loops)
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_env = CustomerSupportEnvironment()

    try:
        while True:
            data        = await websocket.receive_json()
            action_type = data.get("action")

            if action_type == "reset":
                obs = ws_env.reset(
                    task=data.get("task", "classify"),
                    seed=data.get("seed"),
                )
                await websocket.send_json(obs.model_dump())

            elif action_type == "step":
                ticket_action = TicketAction(
                    category=data.get("category", "general"),
                    priority=data.get("priority", "low"),
                    department=data.get("department"),
                    requires_escalation=data.get("requires_escalation"),
                    response=data.get("response"),
                )
                obs, reward, done, info = ws_env.step(ticket_action)
                obs_dict = obs.model_dump()
                obs_dict.pop("reward", None)
                obs_dict.pop("done", None)
                await websocket.send_json({"observation": obs_dict, "reward": reward, "done": done, "info": info})

            elif action_type == "state":
                await websocket.send_json(ws_env.state().model_dump())

            else:
                await websocket.send_json({"error": f"Unknown action: {action_type}"})

    except WebSocketDisconnect:
        pass
