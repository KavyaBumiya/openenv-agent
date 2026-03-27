"""Data models: the contract between agent, environment, and grader."""

from pydantic import BaseModel, Field
from typing import Optional
from .openenv_compat import Action, Observation, State


class TicketAction(Action):
    """What the agent sends when processing a ticket.

    Different tasks require different fields:
    - classify → category, priority
    - route → category, priority, department, requires_escalation
    - resolve → category, priority, department, requires_escalation, response
    """

    category: str = Field(
        ...,
        description=(
            "Ticket category: billing | technical | account | shipping | general. "
            "Determines issue type and routing direction."
        ),
    )

    priority: str = Field(
        ...,
        description=(
            "Priority level: low | medium | high | urgent. "
            "Reflects urgency based on customer impact and sender tier."
        ),
    )

    department: Optional[str] = Field(
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
