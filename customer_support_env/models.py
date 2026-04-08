"""Data models: the contract between agent, environment, and grader."""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Literal, Annotated

# Use real openenv base classes (v0.2.0+)
try:
    from openenv.core import Action, Observation, State
except ImportError:
    try:
        # Fallback for older openenv-core versions
        from openenv_core import Action, Observation, State
    except ImportError:
        # Fallback for compatibility during development
        class Action(BaseModel):
            model_config = ConfigDict(extra='forbid')
        
        class Observation(BaseModel):
            model_config = ConfigDict(extra='forbid')
        
        class State(BaseModel):
            model_config = ConfigDict(extra='forbid')


class TicketAction(Action):
    """What the agent sends when processing a ticket.

    Different tasks require different fields:
    - classify → category, priority
    - route → category, priority, department, requires_escalation
    - resolve → category, priority, department, requires_escalation, response
    """

    category: Literal["billing", "technical", "account", "shipping", "general"] = Field(
        ...,
        description=(
            "Ticket category: billing | technical | account | shipping | general. "
            "Determines issue type and routing direction."
        ),
    )

    priority: Literal["low", "medium", "high", "urgent"] = Field(
        ...,
        description=(
            "Priority level: low | medium | high | urgent. "
            "Reflects urgency based on customer impact and sender tier."
        ),
    )

    department: Optional[Literal["tier1", "tier2", "billing", "engineering", "management"]] = Field(
        None,
        description=(
            "Routing destination: tier1 | tier2 | billing | engineering | management. "
            "Required for route and resolve tasks."
        ),
    )

    requires_escalation: Optional[bool] = Field(
        None,
        description=(
            "True if issue requires supervisor involvement due to severity, "
            "policy exception, security concern, or enterprise customer impact."
        ),
    )

    response: Optional[str] = Field(
        None,
        description=(
            "Customer-facing response message. Required only for resolve task. "
            "Should acknowledge issue, provide next steps or solution, and maintain professional tone."
        ),
    )

    @field_validator("response")
    @classmethod
    def _normalize_response(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    def validate_for_task(self, task_name: str) -> None:
        """Enforce task-specific requirements for route/resolve actions."""
        if task_name in ("route", "resolve") and self.department is None:
            raise ValueError("department is required for route and resolve tasks")
        if task_name == "resolve" and self.response is None:
            raise ValueError("response is required for resolve task")


class TicketObservation(Observation):
    """What the agent reads to make a decision.

    Ground-truth labels are never included here.
    """

    done: Optional[bool] = Field(
        default=None,
        description="Whether this episode is finished."
    )

    reward: Optional[float] = Field(
        default=None,
        description="Reward from the previous action (None on reset)."
    )

    ticket_id: str = Field(
        ...,
        description="Unique identifier for this ticket (example: TKT-001).",
    )

    subject: str = Field(
        ...,
        description="Short subject line summarizing the customer issue.",
    )

    body: str = Field(
        ...,
        description="Full customer message describing the problem.",
    )

    sender_tier: str = Field(
        ...,
        description=(
            "Customer tier: free | premium | enterprise. "
            "Higher tiers should receive higher urgency handling."
        ),
    )

    previous_tickets: int = Field(
        ...,
        description="Number of previous tickets submitted by this customer.",
    )

    open_since_hours: int = Field(
        default=0,
        description=(
            "How many hours this ticket has been open. "
            "Tickets open more than 24 hours face SLA urgency — "
            "priority errors are penalized more heavily for these tickets."
        ),
    )

    sentiment: str = Field(
        default="neutral",
        description=(
            "Customer emotional state: frustrated | angry | positive | neutral | confused | urgent. "
            "For frustrated or angry customers, an empathetic response tone earns a bonus."
        ),
    )

    task_name: str = Field(
        ...,
        description="Task type: classify | route | resolve.",
    )

    task_description: str = Field(
        ...,
        description="Plain-English instruction explaining what the agent must do in this episode.",
    )

    action_schema: str = Field(
        ...,
        description="JSON schema describing required output structure for this task.",
    )

    policy_excerpt: str = Field(
        "",
        description=(
            "Relevant company policy excerpt. Present mainly in resolve task."
        ),
    )

    feedback: str = Field(
        "",
        description="Optional grading explanation from previous step (usually empty in single-step episodes).",
    )


# Strictly bounded float: must be strictly between EPSILON and 1-EPSILON (never at exact boundaries)
_EPSILON = 0.001
StrictBoundedFloat = Annotated[float, Field(ge=_EPSILON, le=1.0 - _EPSILON)]


class TicketReward(BaseModel):
    """Typed reward payload for each step.
    
    All float fields are strictly bounded in [0.001, 0.999] to comply with OpenEnv Phase 2 validation.
    This prevents issues with Pydantic boundary validation and ensures deterministic serialization.
    """

    value: StrictBoundedFloat = Field(
        ...,
        description="Final shaped reward value strictly in (0.001, 0.999) for this step.",
    )

    raw_score: StrictBoundedFloat = Field(
        ...,
        description="Task grader score strictly in (0.001, 0.999) before trajectory shaping penalties.",
    )

    progress_gain: StrictBoundedFloat = Field(
        ...,
        description="Positive improvement compared with best prior score in this episode (strictly in (0.001, 0.999)).",
    )

    repeated_action_penalty: StrictBoundedFloat = Field(
        ...,
        description="Penalty applied when repeating an action signature (strictly in (0.001, 0.999)).",
    )

    extra_step_penalty: StrictBoundedFloat = Field(
        ...,
        description="Penalty applied for additional steps beyond the first (strictly in (0.001, 0.999)).",
    )


class StepInfo(BaseModel):
    """Auxiliary info payload returned by step API."""

    step_count: int = Field(..., ge=1)
    max_steps: int = Field(..., ge=1)
    best_score: float = Field(..., ge=0.0, le=1.0)
    cumulative_reward: float = Field(..., ge=0.0)


class TicketState(State):
    """Internal environment memory (not visible to agent)."""

    episode_id: str = Field(
        default="",
        description="Unique identifier for this episode instance.",
    )

    step_count: int = Field(
        default=0,
        description="Number of steps taken in this episode.",
    )

    task_name: str = Field(
        default="classify",
        description="Task type for this episode.",
    )

    difficulty: str = Field(
        default="easy",
        description="Difficulty level: easy | medium | hard.",
    )

    max_steps: int = Field(
        default=1,
        description="Maximum allowed steps for this episode.",
    )

    best_score: float = Field(
        default=0.0,
        description="Best raw grader score seen so far in this episode.",
    )

    cumulative_reward: float = Field(
        default=0.0,
        description="Sum of shaped rewards emitted across the trajectory.",
    )

    action_history: list[str] = Field(
        default_factory=list,
        description="Normalized action signatures seen during the episode.",
    )
