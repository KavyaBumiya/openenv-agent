"""Customer support RL environment: the core game logic."""

import logging
import random
import re
import uuid
from typing import Dict, Any

from .openenv_compat import Environment

from .models import StepInfo, TicketAction, TicketObservation, TicketReward, TicketState
from .data import TICKETS

# Configure logging
logger = logging.getLogger(__name__)

_STRICT_SCORE_EPSILON = 0.001


def _strict_unit_score(value: float) -> float:
    """Clamp a score to the open interval (0, 1) with stable rounding."""
    return round(min(1.0 - _STRICT_SCORE_EPSILON, max(_STRICT_SCORE_EPSILON, value)), 3)


def _validate_strict_score(score: float, label: str = "score") -> float:
    """Validate and clamp a score to be strictly in (0, 1).
    
    DEFENSIVE: This function ensures NO score ever escapes unclamped.
    
    Args:
        score: The score to validate
        label: Description for logging
    
    Returns:
        Score strictly in (0.001, 0.999)
    
    Raises:
        ValueError: If score is NaN or invalid
    """
    # Check for invalid values
    if not isinstance(score, (int, float)):
        logger.error(f"❌ INVALID SCORE TYPE: {label}={score} (type={type(score).__name__})")
        return _STRICT_SCORE_EPSILON
    
    if score != score:  # NaN check
        logger.error(f"❌ NaN DETECTED: {label}={score}, using epsilon")
        return _STRICT_SCORE_EPSILON
    
    if score == float('inf') or score == float('-inf'):
        logger.error(f"❌ INFINITE SCORE: {label}={score}, using bound")
        return _strict_unit_score(0.5)
    
    # Clamp to strict bounds
    clamped = _strict_unit_score(score)
    
    # Defensive logging: warn if score was exactly 0.0 or 1.0
    if score == 0.0:
        logger.warning(f"⚠️  CLAMPED 0.0 → {clamped}: {label}")
    elif score == 1.0:
        logger.warning(f"⚠️  CLAMPED 1.0 → {clamped}: {label}")
    elif abs(score - clamped) > 0.001:
        logger.warning(f"⚠️  CLAMPED {score:.4f} → {clamped}: {label}")
    
    # Final validation: ensure result is strictly in (0, 1)
    if clamped <= 0.0 or clamped >= 1.0:
        logger.critical(f"❌ VALIDATION FAILED: {label}={clamped} is not strictly in (0, 1)")
        # Emergency fallback
        return 0.5
    
    return clamped


def _term_variants(term: str) -> set[str]:
    """Generate normalized variants of a term for keyword matching.
    
    Handles English inflections including silent-e rule:
    - resolve + ed → resolved (drop silent(e)
    - route + ing → routing (drop silent-e)
    - help + ed → helped (simple addition)
    """
    normalized = term.lower().strip()
    variants = {normalized}
    
    # First pass: try stripping each suffix to find base forms
    for suffix in ("ed", "ing", "s", "tion"):
        if len(normalized) > len(suffix) + 2 and normalized.endswith(suffix):
            base = normalized[: -len(suffix)]
            variants.add(base)
            # For the base form, also try adding other suffixes
            for other_suffix in ("ed", "ing", "s"):
                if other_suffix != suffix and len(base + other_suffix) < 30:
                    variants.add(base + other_suffix)
    
    # Second pass: for the original word, if it's already a base form (no suffix),
    # also add common inflections (handling silent-e rule)
    is_base = not any(
        normalized.endswith(suf) and len(normalized) > len(suf) + 2
        for suf in ("ed", "ing", "s", "tion")
    )
    
    if is_base:
        # For "ing": drop trailing 'e' before adding 'ing'
        if normalized.endswith("e") and len(normalized) > 3:
            variants.add(normalized[:-1] + "ing")  # resolve → resolving
        variants.add(normalized + "ing")  # help → helping
        
        # For "ed": drop trailing 'e' before adding 'ed'
        if normalized.endswith("e") and len(normalized) > 3:
            variants.add(normalized[:-1] + "ed")  # resolve → resolved
        variants.add(normalized + "ed")  # help → helped
        
        # For "s": just add it (usually works)
        variants.add(normalized + "s")  # help → helps
    
    return {v for v in variants if v and len(v) > 2}


class CustomerSupportEnvironment(Environment[TicketAction, TicketObservation, TicketState]):
    """Customer support ticket environment with trajectory-shaped rewards.

    Design:
    - reset() picks a ticket and task
    - step() supports task-dependent multi-step trajectories
    - reward provides partial progress, loop penalties, and time penalties
    """
    
    SUPPORTS_CONCURRENT_SESSIONS = True
    
    # Priority ordering for graduated scoring
    PRIORITY_ORDER = ["low", "medium", "high", "urgent"]
    
    # Task difficulty mapping
    DIFFICULTY_MAP = {
        "classify": "easy",
        "route": "medium",
        "resolve": "hard",
    }
    
    # ============= GRADING CONFIGURATION PARAMETERS =============
    # These constants control how actions are scored. Tune these to adjust difficulty.
    
    # Enterprise customer handling: penalize priority mistakes more for enterprise customers
    ENTERPRISE_PRIORITY_PENALTY = 0.7  # Multiply score by this if enterprise + wrong priority
    
    # SLA urgency modeling: tickets open > 24h are SLA-critical
    SLA_THRESHOLD_HOURS = 24
    SLA_PENALTY_MULTIPLIER = 0.85  # Applied when SLA-critical + priority wrong
    
    # Response quality requirements (resolve task)
    RESPONSE_MIN_LENGTH = 20  # Minimum characters to count as valid response
    RESPONSE_LENGTH_PENALTY = 0.5  # Penalty multiplier if response too short
    RESPONSE_KEYWORD_THRESHOLD = 0.5   # Must match at least half of the required keywords
    RESPONSE_MIN_KEYWORDS_REQUIRED = 3  # Minimum keywords needed regardless of threshold
    
    # Response content penalties
    RESPONSE_ACTION_PHRASE_PENALTY = 0.1  # Reduce score if no concrete action phrases
    RESPONSE_FILLER_PENALTY = 0.3  # Reduce score if mostly filler content

    # Trajectory shaping penalties
    LOOP_PENALTY = 0.15
    EXTRA_STEP_PENALTY = 0.05
    
    # Sentiment-aware response bonuses
    SENTIMENT_EMPATHY_BONUS = 0.1  # Bonus for empathetic response when frustrated customer
    
    # Department fallback scoring (allow partial credit for reasonable alternatives)
    DEPARTMENT_FALLBACK_SCORE = 0.4  # Score for tier1 → tier2 or tier2 ↔ engineering
    DEPARTMENT_EXACT_SCORE = 1.0  # Score for exact match
    
    # Priority distance scoring
    PRIORITY_EXACT_SCORE = 1.0
    
    # Max trajectory length by task difficulty.
    TASK_MAX_STEPS = {
        "classify": 1,
        "route": 2,
        "resolve": 3,
    }
    PRIORITY_ONE_STEP_SCORE = 0.6
    PRIORITY_TWO_STEP_SCORE = 0.2
    PRIORITY_THREE_PLUS_STEP_SCORE = 0.0
    
    # Reward weights per task (updated to include escalation)
    REWARD_WEIGHTS = {
        "classify": {"category": 0.6, "priority": 0.4},
        "route": {"category": 0.35, "priority": 0.25, "department": 0.25, "escalation": 0.15},
        "resolve": {"category": 0.2, "priority": 0.15, "department": 0.2, "escalation": 0.15, "response": 0.3},
    }
    
    # Action schema definitions shown to agent (now with examples)
    ACTION_SCHEMAS = {
        "classify": """{
  "category": "string (required): billing | technical | account | general | shipping",
  "priority": "string (required): low | medium | high | urgent"
}

Example output:
{"category": "billing", "priority": "high"}""",
        "route": """{
  "category": "string (required): billing | technical | account | general | shipping",
  "priority": "string (required): low | medium | high | urgent",
  "department": "string (required): tier1 | tier2 | billing | engineering | management",
  "requires_escalation": "boolean (optional): true if supervisor review needed"
}

Example output:
{"category": "technical", "priority": "high", "department": "engineering", "requires_escalation": false}""",
        "resolve": """{
  "category": "string (required): billing | technical | account | general | shipping",
  "priority": "string (required): low | medium | high | urgent",
  "department": "string (required): tier1 | tier2 | billing | engineering | management",
  "requires_escalation": "boolean (optional): true if supervisor review needed",
  "response": "string (required): Professional customer-facing response message"
}

Example output:
{"category": "billing", "priority": "medium", "department": "billing", "requires_escalation": false, "response": "Thank you for contacting us. We've reviewed your refund request..."}""",
    }
    
    # Task descriptions
    TASK_DESCRIPTIONS = {
        "classify": "Read the customer's ticket and classify it into a category (billing, technical, account, general, or shipping) and assign a priority level (low, medium, high, urgent).",
        "route": "Read the customer's ticket, classify it, assign priority, and determine which department should handle it (tier1, tier2, billing, engineering, or management).",
        "resolve": "Read the customer's ticket, classify it, assign priority, route it to the right department, and draft a professional response addressing their issue.",
    }
    
    # Routing policy that applies to all tasks
    ROUTING_POLICY = """
DEPARTMENT ROUTING POLICY:
- tier1: General questions, FAQ answers, simple troubleshooting, standard refunds (low complexity)
- tier2: Complex technical issues, account investigations, escalation preparation (medium complexity)
- billing: Payment disputes, subscription changes, invoice corrections, refund processing
- engineering: Bug reports, API errors, performance problems, feature requests
- management: VIP retention, compliance/legal matters, contract disputes, security incidents

ESCALATION CRITERIA (requires_escalation=true):
  • Enterprise customer + financial/trust issue
  • Security incident
  • Customer threatening churn
  • Policy exception required
"""
    
    # Policy excerpts for resolve task
    POLICY_EXCERPTS = {
        "billing": "Refund Policy: We offer full refunds within 14 days of purchase for any reason. After 14 days, refunds are issued pro-rated for unused time. Billing errors are corrected immediately with refunds within 3 business days.",
        "technical": "Technical SLA: Critical issues (P1) receive response within 1 hour. High priority (P2) within 4 hours. Medium priority (P3) within 1 business day. We provide product documentation, API debugging, and troubleshooting support.",
        "account": "Account Policy: Users can cancel anytime without penalty. Account deletion is processed within 14 days with complete data removal. Enterprise accounts require management approval.",
        "general": "Company Values: We prioritize customer success, transparency, and community. Partnership opportunities are reviewed by our business development team. Security vulnerabilities are handled as P0 with immediate investigation.",
        "shipping": "Shipping Policy: Orders ship within 2 business days. Free shipping for orders over $50, expedited available for $10. Lost packages are replaced or refunded within 7 business days.",
    }
    
    def __init__(self) -> None:
        """Initialize environment state variables.
        
        Only instance variables that survive between reset() and step()
        """
        # Validate reward weights sum to 1.0 for each task
        for task, weights in self.REWARD_WEIGHTS.items():
            total_weight = sum(weights.values())
            if abs(total_weight - 1.0) >= 1e-9:
                raise ValueError(
                    f"REWARD_WEIGHTS['{task}'] sum to {total_weight}, not 1.0. "
                    f"Weights: {weights}"
                )
        
        self._state: TicketState = TicketState()
        self._ticket: Dict[str, Any] | None = None
        self._task: str = "classify"
    
    def reset(self, seed=None, episode_id=None, task="classify", **kwargs) -> TicketObservation:
        """Reset environment for new episode: pick ticket, set task, initialize state.

        Args:
            seed: Reproducible ticket selector (seed % len(TICKETS) = ticket index). If None, picks randomly.
            episode_id: Episode identifier (generated if not provided)
            task: "classify", "route", or "resolve"
            
        Returns:
            Initial observation with done=False, reward=None
        """
        # Step 1: Pick a reproducible ticket based on seed
        # Using modulo arithmetic: seed % len(TICKETS) ensures any seed works correctly
        # If seed is None, pick randomly without affecting global state
        if seed is not None:
            ticket_index = seed % len(TICKETS)
            self._ticket = TICKETS[ticket_index]
        else:
            # Use a local Random instance to avoid touching global state
            rng = random.Random()
            self._ticket = rng.choice(TICKETS)
        
        self._task = task
        
        # Step 2: Initialize fresh state (no carryover from previous episode)
        self._state = TicketState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            task_name=task,
            difficulty=self.DIFFICULTY_MAP[task],
            max_steps=self.TASK_MAX_STEPS[task],
            best_score=0.0,
            cumulative_reward=0.0,
        )
        
        # Step 3: Return initial observation
        if self._ticket is None:
            raise RuntimeError("reset() must be called before step()")
        
        # Build policy excerpt: routing policy + category-specific policy for resolve task
        policy_excerpt = self.ROUTING_POLICY
        if task == "resolve":
            category_policy = self.POLICY_EXCERPTS.get(self._ticket["category"], "")
            if category_policy:
                policy_excerpt += "\n\n" + category_policy
        
        return TicketObservation(
            ticket_id=self._ticket["id"],
            subject=self._ticket["subject"],
            body=self._ticket["body"],
            sender_tier=self._ticket["tier"],
            open_since_hours=self._ticket.get("open_since_hours", 0),
            sentiment=self._ticket.get("sentiment", "neutral"),
            task_name=task,
            task_description=self.TASK_DESCRIPTIONS[task],
            action_schema=self.ACTION_SCHEMAS[task],
            policy_excerpt=policy_excerpt,
            feedback="",  # No feedback on initial reset
            previous_tickets=self._ticket.get("previous_tickets", 0),
            done=False,  # Explicitly False on reset
            reward=None,  # No reward yet on reset
        )
    
    def step(self, action: TicketAction, timeout_s=None, **kwargs) -> tuple[TicketObservation, float, bool, dict]:
        """Process one action, grade it, return score and feedback.

        Multi-step: done depends on task max steps or near-perfect completion.
        
        Args:
            action: Agent's TicketAction response
            timeout_s: Optional timeout (unused in single-turn)
            
        Returns:
            A 4-tuple of (observation, reward, done, info)
        """
        if self._ticket is None:
            raise RuntimeError("reset() must be called before step()")

        self._state.step_count += 1

        # Enforce task-specific action requirements early.
        action.validate_for_task(self._task)
        
        # Try to grade, gracefully handle malformed actions
        reward_model: TicketReward
        try:
            raw_score = self._grade(action)
            reward_model = self.build_reward(action, raw_score)
            feedback = self._build_feedback(action, raw_score)
        except Exception as e:
            logger.exception("Unexpected grading failure for task %s", self._task)
            raise

        reward = reward_model.value
        self._state.cumulative_reward = round(self._state.cumulative_reward + reward, 3)
        self._state.best_score = round(max(self._state.best_score, raw_score), 3)
        self._state.action_history.append(self._action_signature(action))
        done = self._compute_done(raw_score)
        
        # Return final observation: single-turn always done after one step
        # Build policy excerpt: routing policy + category-specific policy
        policy_excerpt = self.ROUTING_POLICY
        if self._task == "resolve":
            category_policy = self.POLICY_EXCERPTS.get(self._ticket["category"], "")
            if category_policy:
                policy_excerpt += "\n\n" + category_policy
        
        observation = TicketObservation(
            ticket_id=self._ticket["id"],
            subject=self._ticket["subject"],
            body=self._ticket["body"],
            sender_tier=self._ticket["tier"],
            open_since_hours=self._ticket.get("open_since_hours", 0),
            sentiment=self._ticket.get("sentiment", "neutral"),
            task_name=self._task,
            task_description=self.TASK_DESCRIPTIONS[self._task],
            action_schema=self.ACTION_SCHEMAS[self._task],
            policy_excerpt=policy_excerpt,
            feedback=(
                f"{feedback} | step={self._state.step_count}/{self._state.max_steps} "
                f"| best_score={self._state.best_score:.2f} | cumulative_reward={self._state.cumulative_reward:.2f}"
            ),
            previous_tickets=self._ticket.get("previous_tickets", 0),
            done=done,
            reward=reward,
        )

        info = StepInfo(
            step_count=self._state.step_count,
            max_steps=self._state.max_steps,
            best_score=self._state.best_score,
            cumulative_reward=self._state.cumulative_reward,
        ).model_dump()
        
        # Defensive: Validate raw score before adding to info
        validated_raw_score = _validate_strict_score(raw_score, f"step_raw_score[ticket={self._ticket.get('id', 'UNKNOWN')}]")
        
        info.update(
            {
                "raw_score": validated_raw_score,
                "feedback": feedback,
                "reward_breakdown": reward_model.model_dump(),
            }
        )

        return observation, reward, done, info

    def state(self) -> TicketState:
        """Return current state for OpenEnv compatibility."""
        return self._state

    def _compute_done(self, raw_score: float) -> bool:
        if raw_score >= 0.95:
            return True
        return self._state.step_count >= self._state.max_steps

    def build_reward(self, action: TicketAction, raw_score: float) -> TicketReward:
        """Build a typed reward model with transparent shaping components.
        
        DEFENSIVE: All components are validated to be strictly in (0, 1).
        """
        prev_best = self._state.best_score
        progress_gain = max(0.0, raw_score - prev_best)
        step_penalty = self.EXTRA_STEP_PENALTY * max(0, self._state.step_count - 1)
        loop_penalty = self.LOOP_PENALTY if self._action_signature(action) in self._state.action_history else 0.0
        final_reward_raw = max(0.0, progress_gain - step_penalty - loop_penalty)
        
        # Comprehensive validation of all components
        value = _validate_strict_score(final_reward_raw, "reward_value")
        raw_score_clamped = _validate_strict_score(raw_score, "raw_score_component")
        
        return TicketReward(
            value=value,
            raw_score=raw_score_clamped,
            progress_gain=round(progress_gain, 3),  # Can be 0.0 (ge=0.0)
            repeated_action_penalty=round(loop_penalty, 3),  # Can be 0.0 (ge=0.0)
            extra_step_penalty=round(step_penalty, 3),  # Can be 0.0 (ge=0.0)
        )

    def _action_signature(self, action: TicketAction) -> str:
        response = (action.response or "").strip().lower()
        response = re.sub(r"\s+", " ", response)
        return "|".join(
            [
                (action.category or "").strip().lower(),
                (action.priority or "").strip().lower(),
                (action.department or "").strip().lower(),
                str(bool(action.requires_escalation)).lower(),
                response,
            ]
        )
    
    def _grade(self, action: TicketAction) -> float:
        """Score the action against ground truth, applying task-specific weights.
        
        Enhanced with:
        - Enterprise customer priority awareness
        - Escalation correctness
        - SLA urgency modeling
        - Department routing flexibility
        
        Never raises exceptions - returns 0.0 for malformed input.
        
        Returns:
            float in [0.0, 1.0]
        """
        # Normalize inputs (handle None, uppercase, whitespace)
        category = (action.category or "").strip().lower()
        priority = (action.priority or "").strip().lower()
        department = (action.department or "").strip().lower()
        response = (action.response or "").strip()
        
        # Ground truth from dataset
        if self._ticket is None:
            raise RuntimeError("reset() must be called before step()")
        gt_category = self._ticket["category"].lower()
        gt_priority = self._ticket["priority"].lower()
        gt_department = self._ticket["department"].lower()
        gt_response_keywords = self._ticket.get("response_keywords", [])
        gt_escalation = self._ticket.get("requires_escalation", False)
        
        ticket_id = self._ticket.get("id", "UNKNOWN")
        logger.debug(f"Grading action for ticket {ticket_id} (task={self._task})")
        logger.debug(f"  Prediction: category={category}, priority={priority}, dept={department}, escalation={action.requires_escalation}")
        logger.debug(f"  Ground truth: category={gt_category}, priority={gt_priority}, dept={gt_department}, escalation={gt_escalation}")
        
        # Score each component (with comprehensive validation)
        cat_score = _validate_strict_score(1.0 if category == gt_category else 0.0, f"category_score[ticket={ticket_id}]")
        
        # Priority scoring with enterprise penalty
        pri_score_raw = self._score_priority(priority, gt_priority, self._ticket)
        pri_score = _validate_strict_score(pri_score_raw, f"priority_score[ticket={ticket_id}]")
        
        # Department scoring with fallback logic
        dept_score_raw = self._score_department(department, gt_department)
        dept_score = _validate_strict_score(dept_score_raw, f"department_score[ticket={ticket_id}]")
        
        # Escalation scoring
        escalation_score_raw = self._score_escalation(action.requires_escalation, gt_escalation)
        escalation_score = _validate_strict_score(escalation_score_raw, f"escalation_score[ticket={ticket_id}]")
        
        # Response scoring with sentiment awareness
        resp_score_raw = self._score_response(response, gt_response_keywords, self._ticket)
        resp_score = _validate_strict_score(resp_score_raw, f"response_score[ticket={ticket_id}]")
        
        logger.debug(f"  Component scores: cat={cat_score}, pri={pri_score}, dept={dept_score}, esc={escalation_score}, resp={resp_score}")
        
        # Apply task-specific weights
        if self._task == "classify":
            weights = self.REWARD_WEIGHTS["classify"]
            final_score = cat_score * weights["category"] + pri_score * weights["priority"]
        
        elif self._task == "route":
            weights = self.REWARD_WEIGHTS["route"]
            final_score = (
                cat_score * weights["category"]
                + pri_score * weights["priority"]
                + dept_score * weights["department"]
                + escalation_score * weights["escalation"]
            )
        
        else:  # resolve (HARD task)
            weights = self.REWARD_WEIGHTS["resolve"]
            final_score = (
                cat_score * weights["category"]
                + pri_score * weights["priority"]
                + dept_score * weights["department"]
                + escalation_score * weights["escalation"]
                + resp_score * weights["response"]
            )
            
            # HARD task penalty: missing/inadequate response significantly hurts overall score
            # Apply the penalty to the response component only.
            if not response or len(response) < self.RESPONSE_MIN_LENGTH:
                response_component = resp_score * weights["response"] * self.RESPONSE_LENGTH_PENALTY
                final_score = (
                    cat_score * weights["category"]
                    + pri_score * weights["priority"]
                    + dept_score * weights["department"]
                    + escalation_score * weights["escalation"]
                    + response_component
                )
                logger.debug(f"Response penalty applied: too short ({len(response)} chars, min {self.RESPONSE_MIN_LENGTH})")
        
        final_score_raw = round(final_score, 3)
        final_score = _validate_strict_score(final_score_raw, f"final_score[ticket={ticket_id}, task={self._task}]")
        logger.info(f"✅ Final score for ticket {ticket_id} ({self._task}): {final_score:.4f}")
        
        # DEFENSIVE: Ensure result is strictly in (0, 1)
        if not (0 < final_score < 1):
            logger.critical(f"❌❌❌ CRITICAL: Final score {final_score} is NOT strictly in (0,1)!")
            final_score = 0.5  # Emergency fallback
        
        return final_score
    
    def _score_priority(self, predicted: str, actual: str, ticket: Dict[str, Any]) -> float:
        """Graduated priority scoring with enterprise customer awareness.
        
        Key insight: Enterprise customers expect higher urgency handling.
        So enterprise + wrong priority = larger penalty.
        
        Also models SLA urgency: long-open tickets escalate naturally.
        
        Returns:
            1.0 for exact match, 0.6 for one step off, 0.2 for two steps,
            0.0 for three+ steps
            With penalties applied for enterprise/SLA misses
        """
        try:
            pred_idx = self.PRIORITY_ORDER.index(predicted)
            actual_idx = self.PRIORITY_ORDER.index(actual)
            distance = abs(pred_idx - actual_idx)
            
            # Base score from priority distance
            if distance == 0:
                base_score = self.PRIORITY_EXACT_SCORE
            elif distance == 1:
                base_score = self.PRIORITY_ONE_STEP_SCORE
            elif distance == 2:
                base_score = self.PRIORITY_TWO_STEP_SCORE
            else:
                base_score = self.PRIORITY_THREE_PLUS_STEP_SCORE
            
            # Apply enterprise penalty: if enterprise + wrong priority, reduce score
            if ticket.get("tier") == "enterprise" and distance > 0:
                base_score *= self.ENTERPRISE_PRIORITY_PENALTY
            
            # Apply SLA urgency penalty: long-open + wrong priority = bigger penalty
            open_hours = ticket.get("open_since_hours", 0)
            if open_hours > self.SLA_THRESHOLD_HOURS and distance > 0:
                base_score *= self.SLA_PENALTY_MULTIPLIER
            
            logger.debug(f"Priority score: {base_score} (predicted={predicted}, actual={actual}, distance={distance})")
            clamped = _strict_unit_score(round(base_score, 2))
            return clamped
        
        except ValueError:
            # Predicted priority not in valid list
            return _strict_unit_score(0.0)
    
    def _score_department(self, predicted: str, actual: str) -> float:
        """Department routing score with fallback logic.
        
        Real support systems allow some flexibility:
        - tier1 sometimes acceptable even if tier2 correct
        - So we give partial credit for reasonable fallbacks
        
        Returns:
            1.0 for exact match
            0.4 for tier1 when tier2 expected (acceptable fallback)
            0.4 for tier2 when engineering expected, or engineering when tier2 expected
            0.0 otherwise
        """
        if not predicted:
            return 0.0
        
        if predicted == actual:
            return _strict_unit_score(self.DEPARTMENT_EXACT_SCORE)
        
        # Reasonable fallback: tier1 instead of tier2
        if predicted == "tier1" and actual == "tier2":
            return _strict_unit_score(self.DEPARTMENT_FALLBACK_SCORE)

        # Reasonable technical fallback between tier2 triage and engineering.
        if (predicted == "tier2" and actual == "engineering") or (
            predicted == "engineering" and actual == "tier2"
        ):
            return _strict_unit_score(self.DEPARTMENT_FALLBACK_SCORE)
        
        # No fallback credit otherwise
        logger.debug(f"Department score: 0.0 (predicted={predicted}, actual={actual}, no fallback)")
        return _strict_unit_score(0.0)
    
    def _score_escalation(self, predicted: bool | None, actual: bool) -> float:
        """Escalation judgment score.
        
        Assesses whether agent correctly identified supervision-needed cases.
        
        Returns:
            1.0 if correct
            0.0 if incorrect or missing
        """
        if predicted is None:
            # Agent omitted field - treat as False (no escalation)
            predicted = False
        
        return _strict_unit_score(1.0 if predicted == actual else 0.0)
    
    def _score_response(self, response_text: str, required_keywords: list, ticket: Dict[str, Any]) -> float:
        """Score response quality by keyword presence with sentiment awareness.
        
        Response grading criteria:
        1. Includes required keyword signals
        2. Tone matches customer sentiment (frustrated → empathetic)
        3. Actionable and professional
        
        Scoring: Require at least half of keywords (with minimum 3 when applicable), with sentiment bonus.
        
        Returns:
            1.0 if excellent
            0.6 if good
            0.2 if partial
            0.0 if too few keywords
        """
        if not required_keywords:
            return _strict_unit_score(1.0)  # No keywords required, return full credit
        
        response_lower = response_text.lower()
        response_terms = {
            variant
            for token in re.findall(r"\b\w+\b", response_lower)
            for variant in _term_variants(token)
        }

        def _kw_match(kw: str) -> bool:
            return bool(_term_variants(kw) & response_terms)

        found_count = sum(1 for kw in required_keywords if _kw_match(kw))
        
        # Require at least 3 out of N keywords, or half of them, whichever is larger.
        threshold = min(
            len(required_keywords),
            max(self.RESPONSE_MIN_KEYWORDS_REQUIRED, (len(required_keywords) + 1) // 2),
        )
        
        # Base score from keyword coverage
        if found_count >= len(required_keywords):
            base_score = 1.0
        elif found_count >= threshold:
            base_score = 0.6
        elif found_count >= 1:
            base_score = 0.2
        else:
            logger.debug(f"Response insufficient keywords: {found_count}/{len(required_keywords)} (threshold={threshold})")
            return _strict_unit_score(0.0)  # Too few keywords

        # Actionability requirement: concrete next-step phrasing should be present.
        action_phrases = ["we will", "next steps", "please", "within", "today", "hours", "days"]
        has_action_phrase = any(phrase in response_lower for phrase in action_phrases)
        if not has_action_phrase:
            base_score = max(0.0, base_score - self.RESPONSE_ACTION_PHRASE_PENALTY)
            logger.debug(f"Response missing action phrase: reducing score by {self.RESPONSE_ACTION_PHRASE_PENALTY}")

        # Penalize filler-heavy responses that game keywords without concrete content.
        filler_markers = ["as an ai", "cannot assist", "lorem", "blah", "template"]
        if any(marker in response_lower for marker in filler_markers):
            base_score = max(0.0, base_score - self.RESPONSE_FILLER_PENALTY)
            logger.debug(f"Response contains filler: reducing score by {self.RESPONSE_FILLER_PENALTY}")
        
        # Boost score if sentiment-matched
        sentiment = ticket.get("sentiment", "neutral").lower()
        empathy_keywords = ["sorry", "understand", "apologize", "thank you", "appreciate", "happy to help"]
        has_empathy = any(ek in response_lower for ek in empathy_keywords)
        
        # Frustrated/angry customers → reward empathy
        if sentiment in ["frustrated", "angry", "distressed"] and has_empathy:
            base_score = min(1.0, base_score + self.SENTIMENT_EMPATHY_BONUS)  # Bonus for emotional intelligence
            logger.debug(f"Empathy bonus applied: +{self.SENTIMENT_EMPATHY_BONUS}")
        
        return _strict_unit_score(round(base_score, 2))
    
    def _build_feedback(self, action: TicketAction, score: float) -> str:
        """Build human-readable explanation of the grade.
        
        Includes:
        - Category/priority/department correctness
        - Escalation judgment assessment
        - Response quality feedback (if resolve task)
        - Overall quality rating
        
        Used for grading transparency and debugging.
        """
        if self._ticket is None:
            raise RuntimeError("reset() must be called before step()")
        gt_category = self._ticket["category"]
        gt_priority = self._ticket["priority"]
        gt_department = self._ticket["department"]
        gt_escalation = self._ticket.get("requires_escalation", False)
        
        pred_category = (action.category or "").strip().lower()
        pred_priority = (action.priority or "").strip().lower()
        pred_department = (action.department or "").strip().lower()
        
        feedback_parts = []
        
        # Category feedback
        if pred_category.lower() == gt_category.lower():
            feedback_parts.append(f"✓ Category correct: {gt_category}")
        else:
            feedback_parts.append(f"✗ Category: '{action.category}' (expected '{gt_category}')")
        
        # Priority feedback with distance info
        if pred_priority.lower() == gt_priority.lower():
            feedback_parts.append(f"✓ Priority correct: {gt_priority}")
        else:
            try:
                distance = abs(
                    self.PRIORITY_ORDER.index(pred_priority) -
                    self.PRIORITY_ORDER.index(gt_priority)
                )
                if distance == 1:
                    feedback_parts.append(f"~ Priority close: '{action.priority}' vs '{gt_priority}' (1 step)")
                else:
                    feedback_parts.append(f"✗ Priority: '{action.priority}' (expected '{gt_priority}')")
            except ValueError:
                feedback_parts.append(f"✗ Priority: invalid '{action.priority}' (expected '{gt_priority}')")
        
        # Department feedback (if task requires it)
        if self._task in ["route", "resolve"]:
            if pred_department.lower() == gt_department.lower():
                feedback_parts.append(f"✓ Department correct: {gt_department}")
            else:
                feedback_parts.append(f"✗ Department: '{action.department}' (expected '{gt_department}')")
        
        # Escalation feedback (if task requires it)
        if self._task in ["route", "resolve"]:
            if action.requires_escalation == gt_escalation:
                feedback_parts.append(f"✓ Escalation judgment correct: {gt_escalation}")
            else:
                feedback_parts.append(f"✗ Escalation: {action.requires_escalation} (expected {gt_escalation})")
        
        # Response feedback (if task requires it)
        if self._task == "resolve":
            if self._ticket is None:
                raise RuntimeError("reset() must be called before step()")
            gt_keywords = self._ticket.get("response_keywords", [])
            response_text = (action.response or "").strip()
            
            # Check if response is too short
            if not response_text or len(response_text) < 20:
                feedback_parts.append(f"✗ Response required for HARD task (PENALTY: -50% for incomplete resolve)")
            else:
                response_lower = response_text.lower()
                response_terms = {
                    variant
                    for token in re.findall(r"\b\w+\b", response_lower)
                    for variant in _term_variants(token)
                }

                found = [kw for kw in gt_keywords if _term_variants(kw) & response_terms]
                
                missing = [kw for kw in gt_keywords if kw not in found]
                feedback_parts.append(
                    f"Response: {len(found)}/{len(gt_keywords)} keywords found. Missing: {missing if missing else 'none'}"
                )
        
        # Overall score context
        if score >= 0.9:
            quality = "Excellent"
        elif score >= 0.7:
            quality = "Good"
        elif score >= 0.5:
            quality = "Partial"
        else:
            quality = "Needs improvement"
        
        return f"{' | '.join(feedback_parts)} | Score: {quality} ({score:.2f})"
