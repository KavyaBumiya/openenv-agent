"""
Curriculum Learning Manager: Progressive difficulty adjustment.

Curriculum learning helps agents learn more effectively by:
- Starting with easy tasks
- Progressively increasing difficulty
- Adapting based on performance

"""

import logging
from typing import Literal
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CurriculumStage:
    """One stage in the curriculum."""
    stage_number: int
    task_subset: list[str]  # Which tasks to include: ["classify"], ["classify", "route"], etc
    min_success_rate: float  # Minimum success rate to advance (0.0-1.0)
    max_steps: int  # Maximum steps allowed in this stage
    difficulty_level: Literal["easy", "medium", "hard", "expert"]
    description: str


class CurriculumManager:
    """Manage progressive curriculum for agent training."""
    
    # Default curriculum: 4 stages
    DEFAULT_CURRICULUM = [
        CurriculumStage(
            stage_number=1,
            task_subset=["classify"],
            min_success_rate=0.7,
            max_steps=100,
            difficulty_level="easy",
            description="Stage 1: Learn to classify tickets accurately"
        ),
        CurriculumStage(
            stage_number=2,
            task_subset=["classify", "route"],
            min_success_rate=0.65,
            max_steps=300,
            difficulty_level="easy",
            description="Stage 2: Learn routing in addition to classification"
        ),
        CurriculumStage(
            stage_number=3,
            task_subset=["classify", "route", "resolve"],
            min_success_rate=0.60,
            max_steps=1000,
            difficulty_level="medium",
            description="Stage 3: Learn complete ticket resolution"
        ),
        CurriculumStage(
            stage_number=4,
            task_subset=["classify", "route", "resolve"],
            min_success_rate=0.55,
            max_steps=3000,
            difficulty_level="hard",
            description="Stage 4: Master all tasks at higher difficulty"
        ),
    ]
    
    def __init__(self, curriculum: list[CurriculumStage] | None = None):
        """Initialize with optional custom curriculum."""
        self.curriculum = curriculum or self.DEFAULT_CURRICULUM
        self.current_stage = 0
        self.episode_count = 0
        self.total_steps = 0
        self.stage_successes = 0
        self.stage_attempts = 0
    
    @property
    def current_difficulty(self) -> Literal["easy", "medium", "hard", "expert"]:
        """Get current difficulty level."""
        if self.current_stage < len(self.curriculum):
            return self.curriculum[self.current_stage].difficulty_level
        return "expert"
    
    @property
    def current_task_subset(self) -> list[str]:
        """Get current allowed tasks."""
        if self.current_stage < len(self.curriculum):
            return self.curriculum[self.current_stage].task_subset
        return ["classify", "route", "resolve"]
    
    @property
    def current_stage_info(self) -> CurriculumStage:
        """Get current stage information."""
        return self.curriculum[min(self.current_stage, len(self.curriculum) - 1)]
    
    def record_episode(self, task: str, success: bool, num_steps: int):
        """Record episode result for curriculum progression."""
        self.episode_count += 1
        self.total_steps += num_steps
        self.stage_attempts += 1
        
        if success:
            self.stage_successes += 1
        
        # Check if we should advance to next stage
        if self.stage_attempts >= 50:  # After 50 episodes
            success_rate = self.stage_successes / self.stage_attempts
            required_rate = self.current_stage_info.min_success_rate
            
            if success_rate >= required_rate and self.current_stage < len(self.curriculum) - 1:
                logger.info(
                    f"🎓 Curriculum advancement: Stage {self.current_stage + 1} → {self.current_stage + 2} "
                    f"(success rate: {success_rate:.1%} >= {required_rate:.1%})"
                )
                self.current_stage += 1
                self.stage_successes = 0
                self.stage_attempts = 0
    
    def get_progress_summary(self) -> dict:
        """Get human-readable curriculum progress."""
        return {
            "stage": self.current_stage + 1,
            "total_stages": len(self.curriculum),
            "current_difficulty": self.current_difficulty,
            "available_tasks": self.current_task_subset,
            "episodes_in_stage": self.stage_attempts,
            "success_rate_in_stage": (
                self.stage_successes / self.stage_attempts
                if self.stage_attempts > 0 else 0.0
            ),
            "total_episodes": self.episode_count,
            "total_steps": self.total_steps,
            "stage_description": self.current_stage_info.description,
        }


# Custom curriculum example: Focused on resolve task
RESOLVE_FOCUSED_CURRICULUM = [
    CurriculumStage(
        stage_number=1,
        task_subset=["resolve"],  # Only resolve from the start
        min_success_rate=0.5,
        max_steps=500,
        difficulty_level="easy",
        description="Stage 1: Focus on high-quality responses"
    ),
    CurriculumStage(
        stage_number=2,
        task_subset=["resolve"],
        min_success_rate=0.5,
        max_steps=1000,
        difficulty_level="medium",
        description="Stage 2: Response quality under stricter evaluation"
    ),
    CurriculumStage(
        stage_number=3,
        task_subset=["resolve"],
        min_success_rate=0.5,
        max_steps=2000,
        difficulty_level="hard",
        description="Stage 3: Expert-level response evaluation"
    ),
]
