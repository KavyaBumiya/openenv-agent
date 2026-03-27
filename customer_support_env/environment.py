"""Customer support RL environment: the core game logic."""

import random
import uuid
from typing import Dict, Any

from .openenv_compat import Environment

from .models import TicketAction, TicketObservation, TicketState
from .data import TICKETS


class CustomerSupportEnvironment(Environment[TicketAction, TicketObservation, TicketState]):
    """Single-turn ticket processing environment.
    
    Design: Each episode is one ticket, one task, one action.
    - reset() picks a ticket and task
    - step() processes the action, grades it, returns done=True
    - Reward encodes task performance with shaped signals
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
    
    def step(self, action: TicketAction, timeout_s=None, **kwargs) -> TicketObservation:
        """Process one action, grade it, return score and feedback.
        
        Single-turn: always returns done=True after one step.
        
        Args:
            action: Agent's TicketAction response
            timeout_s: Optional timeout (unused in single-turn)
            
        Returns:
            Final observation with done=True, reward, and feedback
        """
        if self._ticket is None:
            raise RuntimeError("reset() must be called before step()")

        self._state.step_count += 1

        # Enforce task-specific action requirements early.
        action.validate_for_task(self._task)
        
        # Try to grade, gracefully handle malformed actions
        try:
            reward = self._grade(action)
            feedback = self._build_feedback(action, reward)
        except Exception as e:
            reward = 0.0
            feedback = f"Could not grade action: {str(e)}"
        
        # Return final observation: single-turn always done after one step
        # Build policy excerpt: routing policy + category-specific policy
        policy_excerpt = self.ROUTING_POLICY
        if self._task == "resolve":
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
            task_name=self._task,
            task_description=self.TASK_DESCRIPTIONS[self._task],
            action_schema=self.ACTION_SCHEMAS[self._task],
            policy_excerpt=policy_excerpt,
            feedback=feedback,
            previous_tickets=self._ticket.get("previous_tickets", 0),
            done=True,
            reward=reward,
        )
    
    @property
    def state(self) -> TicketState:
        """Access current state (uses @property, no parentheses)."""
        return self._state
    
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
        
        # Score each component
        cat_score = 1.0 if category == gt_category else 0.0
        
        # Priority scoring with enterprise penalty
        pri_score = self._score_priority(priority, gt_priority, self._ticket)
        
        # Department scoring with fallback logic
        dept_score = self._score_department(department, gt_department)
        
        # Escalation scoring
        escalation_score = self._score_escalation(action.requires_escalation, gt_escalation)
        
        # Response scoring with sentiment awareness
        resp_score = self._score_response(response, gt_response_keywords, self._ticket)
        
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
            # If response is missing or too short, apply multiplier penalty
            if not response or len(response) < 20:
                final_score *= 0.5  # 50% penalty for incomplete resolve attempts
        
        return round(final_score, 3)
    
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
                base_score = 1.0
            elif distance == 1:
                base_score = 0.6
            elif distance == 2:
                base_score = 0.2
            else:
                base_score = 0.0
            
            # Apply enterprise penalty: if enterprise + wrong priority, reduce score
            if ticket.get("tier") == "enterprise" and distance > 0:
                base_score *= 0.7  # Enterprise customers: higher bar
            
            # Apply SLA urgency penalty: long-open + wrong priority = bigger penalty
            open_hours = ticket.get("open_since_hours", 0)
            if open_hours > 24 and distance > 0:
                base_score *= 0.85  # Urgent latency visible in open_hours
            
            return round(base_score, 2)
        
        except ValueError:
            # Predicted priority not in valid list
            return 0.0
    
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
            return 1.0
        
        # Reasonable fallback: tier1 instead of tier2
        if predicted == "tier1" and actual == "tier2":
            return 0.4

        # Reasonable technical fallback between tier2 triage and engineering.
        if (predicted == "tier2" and actual == "engineering") or (
            predicted == "engineering" and actual == "tier2"
        ):
            return 0.4
        
        # No fallback credit otherwise
        return 0.0
    
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
        
        return 1.0 if predicted == actual else 0.0
    
    def _score_response(self, response_text: str, required_keywords: list, ticket: Dict[str, Any]) -> float:
        """Score response quality by keyword presence with sentiment awareness.
        
        Response grading criteria:
        1. Includes required keyword signals
        2. Tone matches customer sentiment (frustrated → empathetic)
        3. Actionable and professional
        
        Scoring: Require 75% of keywords, with sentiment bonus.
        
        Returns:
            1.0 if excellent
            0.6 if good
            0.3 if partial
            0.0 if too few keywords
        """
        if not required_keywords:
            return 1.0  # No keywords required, return full credit
        
        response_lower = response_text.lower()

        def _kw_match(kw: str, text: str) -> bool:
            # Light stemming for common suffixes to reduce morphology brittleness.
            variants = {kw.lower()}
            for suffix in ("ed", "ing", "s", "tion"):
                if kw.lower().endswith(suffix) and len(kw) > len(suffix) + 2:
                    variants.add(kw.lower()[: -len(suffix)])
            return any(v and v in text for v in variants)

        found_count = sum(1 for kw in required_keywords if _kw_match(kw, response_lower))
        
        # Require at least 3 out of N keywords, or 75% of them
        threshold = max(3, int(len(required_keywords) * 0.75))
        
        # Base score from keyword coverage
        if found_count >= len(required_keywords):
            base_score = 1.0
        elif found_count >= threshold:
            base_score = 0.6
        elif found_count >= len(required_keywords) / 2:
            base_score = 0.3
        else:
            return 0.0  # Too few keywords

        # Actionability requirement: concrete next-step phrasing should be present.
        action_phrases = ["we will", "next steps", "please", "within", "today", "hours", "days"]
        has_action_phrase = any(phrase in response_lower for phrase in action_phrases)
        if not has_action_phrase:
            base_score = max(0.0, base_score - 0.2)

        # Penalize filler-heavy responses that game keywords without concrete content.
        filler_markers = ["as an ai", "cannot assist", "lorem", "blah", "template"]
        if any(marker in response_lower for marker in filler_markers):
            base_score = max(0.0, base_score - 0.3)
        
        # Boost score if sentiment-matched
        sentiment = ticket.get("sentiment", "neutral").lower()
        empathy_keywords = ["sorry", "understand", "apologize", "thank you", "appreciate", "happy to help"]
        has_empathy = any(ek in response_lower for ek in empathy_keywords)
        
        # Frustrated/angry customers → reward empathy
        if sentiment in ["frustrated", "angry", "distressed"] and has_empathy:
            base_score = min(1.0, base_score + 0.1)  # Bonus for emotional intelligence
        
        return round(base_score, 2)
    
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
                found = [kw for kw in gt_keywords if kw.lower() in response_lower]
                missing = [kw for kw in gt_keywords if kw.lower() not in response_lower]
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
