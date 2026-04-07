"""
Reward Configuration: Parameterized, tunable, and curriculum-aware.

This replaces hardcoded constants with a configurable system.
Use for:
- A/B testing different reward schedules
- Curriculum learning (annealing difficulty)
- Reproducible experiments
"""

from pydantic import BaseModel, Field
from typing import Literal


class RewardConfig(BaseModel):
    """Parameterized reward schedule for training agents."""
    
    # ==================== PRIORITY PENALTIES ====================
    priority_exact_match: float = Field(
        default=1.0,
        description="Score for exact priority match"
    )
    priority_one_step_off: float = Field(
        default=0.6,
        description="Score when priority is one step away from correct"
    )
    priority_two_steps_off: float = Field(
        default=0.2,
        description="Score when priority is two or more steps away"
    )
    
    # ==================== PENALTY MULTIPLIERS ====================
    enterprise_priority_penalty: float = Field(
        default=0.15,
        description="Deduction for enterprise customer + wrong priority"
    )
    sla_penalty: float = Field(
        default=0.15,
        description="Deduction when ticket is SLA-critical (>24h) + wrong priority"
    )
    
    # ==================== RESPONSE QUALITY ====================
    response_min_length: int = Field(
        default=20,
        description="Minimum characters for valid response"
    )
    response_keyword_weight: float = Field(
        default=0.6,
        description="How much keyword coverage contributes to response score"
    )
    empathy_bonus: float = Field(
        default=0.1,
        description="Bonus for empathetic response to frustrated customer"
    )
    
    # ==================== DEPARTMENT ROUTING ====================
    department_exact_match: float = Field(
        default=1.0,
        description="Score for exact department match"
    )
    department_fallback_score: float = Field(
        default=0.4,
        description="Score for reasonable fallback (tier1→tier2, tier2↔engineering)"
    )
    
    # ==================== TRAJECTORY PENALTIES ====================
    extra_step_penalty: float = Field(
        default=0.05,
        description="Penalty per extra step beyond minimum"
    )
    repeated_action_penalty: float = Field(
        default=0.15,
        description="Penalty for repeating the same action (loop prevention)"
    )
    
    # ==================== CURRICULUM PARAMETERS ====================
    difficulty_level: Literal["easy", "medium", "hard", "expert"] = Field(
        default="medium",
        description="Current difficulty level - affects penalty annealing"
    )
    step_number: int = Field(
        default=0,
        description="Current training step - for curriculum annealing"
    )
    
    # ==================== WEIGHT OVERRIDES ====================
    # Allow per-task weight customization
    classify_weights: dict | None = Field(
        default=None,
        description="Override default weights for classify task (category, priority)"
    )
    route_weights: dict | None = Field(
        default=None,
        description="Override default weights for route task (category, priority, department, escalation)"
    )
    resolve_weights: dict | None = Field(
        default=None,
        description="Override default weights for resolve task (category, priority, department, escalation, response)"
    )
    
    def get_default_weights(self, task: str) -> dict:
        """Get effective weights for a task (user override or default)."""
        if task == "classify":
            return self.classify_weights or {"category": 0.6, "priority": 0.4}
        elif task == "route":
            return self.route_weights or {
                "category": 0.35,
                "priority": 0.25,
                "department": 0.25,
                "escalation": 0.15,
            }
        elif task == "resolve":
            return self.resolve_weights or {
                "category": 0.15,
                "priority": 0.15,
                "department": 0.15,
                "escalation": 0.15,
                "response": 0.4,
            }
        else:
            raise ValueError(f"Unknown task: {task}")
    
    def get_annealed_penalty(self, base_penalty: float, penalty_type: str = "standard") -> float:
        """Apply curriculum-based annealing to penalties.
        
        As agent trains, reduce penalties to allow exploration.
        """
        # Annealing schedule based on difficulty level
        annealing_factor = {
            "easy": 0.5,      # Easy mode: half penalties
            "medium": 1.0,    # Standard mode: full penalties
            "hard": 1.3,      # Hard mode: increased penalties
            "expert": 1.6,    # Expert mode: strict penalties
        }.get(self.difficulty_level, 1.0)
        
        return base_penalty * annealing_factor
    
    @classmethod
    def preset_easy(cls) -> "RewardConfig":
        """Preset: Easy mode for initial exploration."""
        return cls(
            difficulty_level="easy",
            enterprise_priority_penalty=0.05,
            sla_penalty=0.05,
            extra_step_penalty=0.02,
            repeated_action_penalty=0.05,
        )
    
    @classmethod
    def preset_medium(cls) -> "RewardConfig":
        """Preset: Medium mode (default)."""
        return cls(difficulty_level="medium")
    
    @classmethod
    def preset_hard(cls) -> "RewardConfig":
        """Preset: Hard mode for challenging evaluation."""
        return cls(
            difficulty_level="hard",
            enterprise_priority_penalty=0.20,
            sla_penalty=0.20,
            extra_step_penalty=0.08,
            repeated_action_penalty=0.20,
        )
    
    @classmethod
    def preset_expert(cls) -> "RewardConfig":
        """Preset: Expert mode (competition/evaluation)."""
        return cls(
            difficulty_level="expert",
            enterprise_priority_penalty=0.25,
            sla_penalty=0.25,
            extra_step_penalty=0.10,
            repeated_action_penalty=0.25,
            empathy_bonus=0.05,  # Harder to get bonus
        )


# Global default config
DEFAULT_REWARD_CONFIG = RewardConfig()
