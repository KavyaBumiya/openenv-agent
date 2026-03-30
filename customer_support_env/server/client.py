"""WebSocket client: serializes Python objects to/from JSON."""

import asyncio
import json
from typing import Optional
import websockets

from ..openenv_compat import EnvClient, StepResult

from ..models import TicketAction, TicketObservation, TicketState


class CustomerSupportClient(EnvClient[TicketAction, TicketObservation, TicketState]):
    """WebSocket client for communicating with CustomerSupportEnvironment server.
    
    Handles serialization to/from JSON and WebSocket protocol.
    Converts Python types ↔ JSON for transmission.
    
    Usage:
        client = CustomerSupportClient("ws://localhost:8000/ws")
        await client.connect()
        obs = await client.reset(task="classify", seed=0)
        result = await client.step(action)
        await client.disconnect()
    """
    
    def __init__(self, uri: str):
        """Initialize client with server URI.
        
        Args:
            uri: WebSocket URI, e.g., "ws://localhost:8000/ws"
        """
        self.uri = uri
        self.websocket = None
    
    async def connect(self) -> None:
        """Connect to WebSocket server.
        
        Raises:
            ConnectionError: If connection fails
        """
        try:
            self.websocket = await websockets.connect(self.uri)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.uri}: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
    
    async def reset(self, task: str = "classify", seed: Optional[int] = None) -> TicketObservation:
        """Send reset command to server.
        
        Args:
            task: "classify", "route", or "resolve"
            seed: Random seed for reproducibility (optional)
            
        Returns:
            Initial observation
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.websocket:
            raise RuntimeError("Not connected. Call connect() first.")
        
        payload = {
            "action": "reset",
            "task": task,
        }
        if seed is not None:
            payload["seed"] = seed
        
        await self.websocket.send(json.dumps(payload))
        response = await self.websocket.recv()
        data = json.loads(response)
        
        return self._parse_observation(data)
    
    async def step(self, action: TicketAction) -> StepResult:
        """Send action to server and receive result.
        
        Args:
            action: TicketAction with category, priority, etc.
            
        Returns:
            StepResult with observation, reward, done flag
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.websocket:
            raise RuntimeError("Not connected. Call connect() first.")
        
        payload = {
            "action": "step",
            "category": action.category,
            "priority": action.priority,
            "department": action.department,
            "response": action.response,
            "requires_escalation": action.requires_escalation,
        }
        
        await self.websocket.send(json.dumps(payload))
        response = await self.websocket.recv()
        data = json.loads(response)
        
        return self._parse_result(data)
    
    def _parse_observation(self, payload: dict) -> TicketObservation:
        """Convert JSON payload to TicketObservation."""
        return TicketObservation(
            ticket_id=payload.get("ticket_id", ""),
            subject=payload.get("subject", ""),
            body=payload.get("body", ""),
            sender_tier=payload.get("sender_tier", ""),
            open_since_hours=payload.get("open_since_hours", 0),
            sentiment=payload.get("sentiment", "neutral"),
            task_name=payload.get("task_name", "classify"),
            task_description=payload.get("task_description", ""),
            action_schema=payload.get("action_schema", "{}"),
            policy_excerpt=payload.get("policy_excerpt", ""),
            feedback=payload.get("feedback", ""),
            previous_tickets=payload.get("previous_tickets", 0),
            done=payload.get("done", False),
            reward=payload.get("reward"),
        )
    
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
