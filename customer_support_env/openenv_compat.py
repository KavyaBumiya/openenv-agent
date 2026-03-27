"""Compatibility layer for openenv.core.env_server.

This module provides stub base classes that the environment and models depend on.
Since the installed openenv package doesn't have these, we provide them locally.
"""

from typing import TypeVar, Generic, Dict, Any
from pydantic import BaseModel, ConfigDict

# Type variables for generic environment
ActionType = TypeVar('ActionType')
ObservationType = TypeVar('ObservationType')
StateType = TypeVar('StateType')


class Action(BaseModel):
    """Base class for environment actions."""
    model_config = ConfigDict(extra='forbid')


class Observation(BaseModel):
    """Base class for environment observations."""
    model_config = ConfigDict(extra='forbid')
    
    def __init__(self, **data: Any) -> None:
        """Initialize observation with validated fields."""
        super().__init__(**data)


class State(BaseModel):
    """Base class for environment state."""
    model_config = ConfigDict(extra='forbid')


class StepResult:
    """Result of stepping through the environment."""
    
    def __init__(self, observation, reward: float, done: bool):
        self.observation = observation
        self.reward = reward
        self.done = done


class Environment(Generic[ActionType, ObservationType, StateType]):
    """Base class for RL environments.
    
    Generic over action type, observation type, and state type.
    """
    
    def __init__(self):
        """Initialize the environment."""
        self.state: StateType | None = None
        self.done = False
    
    def reset(self) -> ObservationType:
        """Reset the environment and return initial observation."""
        raise NotImplementedError
    
    def step(self, action: ActionType) -> tuple[ObservationType, float, bool, Dict[str, Any]]:
        """Execute one step with the given action.
        
        Returns:
            observation: Current observation
            reward: Reward for this step
            done: Whether episode is finished
            info: Additional info dict
        """
        raise NotImplementedError
    
    def get_state(self) -> StateType:
        """Get the current state."""
        raise NotImplementedError


class EnvClient(Generic[ActionType, ObservationType, StateType]):
    """Base class for environment clients (e.g., WebSocket communication)."""
    
    def _step_payload(self, action: ActionType) -> dict:
        """Convert action to JSON-serializable dict."""
        raise NotImplementedError
    
    def _observation_from_payload(self, payload: dict) -> ObservationType:
        """Convert JSON payload to observation."""
        raise NotImplementedError


def create_fastapi_app(env_class):
    """Create a FastAPI app for the given environment class.
    
    This is a placeholder that returns a basic FastAPI app.
    The actual implementation would create REST/WebSocket endpoints.
    """
    from fastapi import FastAPI
    
    app = FastAPI(title=env_class.__name__)
    
    @app.get("/health")
    def health():
        """Health check endpoint."""
        return {"status": "ok"}
    
    @app.get("/state")
    def get_state():
        """Get current environment state."""
        return {"status": "not implemented"}
    
    return app
