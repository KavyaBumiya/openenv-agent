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
        self.done = False

    def state(self) -> StateType:
        """Return current environment state."""
        raise NotImplementedError
    
    def reset(self) -> ObservationType:
        """Reset the environment and return initial observation."""
        raise NotImplementedError
    
    def step(self, action: ActionType) -> ObservationType:
        """Execute one step with the given action.
        
        Returns:
            Final observation after processing action.
        """
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
    """Create a FastAPI app with bare initialization (no pre-registered routes).
    
    Routes must be registered in server/app.py to avoid conflicts.
    This function only sets up the app metadata and middleware.
    """
    from fastapi import FastAPI
    
    app = FastAPI(
        title=f"{env_class.__name__} OpenEnv",
        description="OpenEnv-compliant RL environment",
        version="0.1.0"
    )
    
    return app
