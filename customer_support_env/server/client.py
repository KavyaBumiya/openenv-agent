"""WebSocket client: serializes Python objects to/from JSON."""

from ..openenv_compat import EnvClient, StepResult

from ..models import TicketAction, TicketObservation, TicketState


class CustomerSupportClient(EnvClient[TicketAction, TicketObservation, TicketState]):
    """Converts TicketAction ↔ JSON and JSON ↔ TicketObservation.
    
    The radio operator between your Python environment and the agent.
    """
    
    def _step_payload(self, action: TicketAction) -> dict:
        """Convert Action to dict for JSON transmission over WebSocket.
        
        This is what travels over the wire to the server.
        Every field from TicketAction must be included.
        """
        return {
            "category": action.category,
            "priority": action.priority,
            "department": action.department,
            "response": action.response,
            "requires_escalation": action.requires_escalation,
        }
    
    def _parse_result(self, payload: dict) -> StepResult:
        """Reconstruct TicketObservation from server's JSON response.
        
        The server returns JSON. We rebuild our typed TicketObservation.
        For missing fields, we use safe defaults (empty string for text, None for optional).
        """
        obs_data = payload.get("observation", {})
        
        observation = TicketObservation(
            done=payload.get("done", False),
            reward=payload.get("reward"),
            ticket_id=obs_data.get("ticket_id", ""),
            subject=obs_data.get("subject", ""),
            body=obs_data.get("body", ""),
            sender_tier=obs_data.get("sender_tier", ""),
            open_since_hours=obs_data.get("open_since_hours", 0),
            sentiment=obs_data.get("sentiment", "neutral"),
            task_name=obs_data.get("task_name", "classify"),
            task_description=obs_data.get("task_description", ""),
            action_schema=obs_data.get("action_schema", "{}"),
            policy_excerpt=obs_data.get("policy_excerpt", ""),
            feedback=obs_data.get("feedback", ""),
            previous_tickets=obs_data.get("previous_tickets", 0),
        )
        
        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )
    
    def _parse_state(self, payload: dict) -> TicketState:
        """Reconstruct TicketState from server's JSON response.
        
        State metadata: episode tracking and task info.
        """
        return TicketState(
            episode_id=payload.get("episode_id", ""),
            step_count=payload.get("step_count", 0),
            task_name=payload.get("task_name", "classify"),
            difficulty=payload.get("difficulty", "easy"),
        )
