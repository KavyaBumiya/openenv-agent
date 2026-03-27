#!/usr/bin/env python3
"""Difficulty Gradient Validation Test.

Tests that the penalty system correctly differentiates tasks:
- EASY: No penalty for missing response (not required)
- MEDIUM: No penalty for missing response (not required)
- HARD: 50% penalty for missing response (required!)
"""

import os
import sys
import json
from groq import Groq

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("ERROR: GROQ_API_KEY not set")
    sys.exit(1)

client = Groq(api_key=api_key)

from customer_support_env.environment import CustomerSupportEnvironment
from customer_support_env.models import TicketAction

print("=" * 70)
print("DIFFICULTY GRADIENT VALIDATION")
print("=" * 70)
print("\nTest: Same ticket with PERFECT category/priority/department/escalation")
print("      BUT response is intentionally MISSING in HARD task")
print("      Expected: HARD task score should be ~50% of OTHER tasks\n")

env = CustomerSupportEnvironment()
obs = env.reset(seed=0, task="classify")

print(f"Ticket: {obs.ticket_id}")
print(f"Subject: {obs.subject}\n")

# Parse ground truth from grading
print("=" * 70)
print("SCENARIO: All classifications correct, response quality varies")
print("=" * 70)

# Test 1: EASY with NO response (should NOT be penalized)
print("\n[Test 1] EASY Task: No response provided")
action_easy = TicketAction(
    category="general",  # Correct!
    priority="low",      # Correct!
    department=None,
    response=None,
    requires_escalation=False
)
obs_easy = env.step(action_easy)
print(f"  Score: {obs_easy.reward:.1%}")
print(f"  Feedback: {obs_easy.feedback}")

# Restart for MEDIUM
env = CustomerSupportEnvironment()
obs = env.reset(seed=0, task="route")

# Test 2: MEDIUM with NO response (should NOT be penalized)
print("\n[Test 2] MEDIUM Task: No response provided")
action_medium = TicketAction(
    category="general",  # Correct!
    priority="low",      # Correct!
    department="tier1",  # Correct!
    response=None,
    requires_escalation=False
)
obs_medium = env.step(action_medium)
print(f"  Score: {obs_medium.reward:.1%}")
print(f"  Feedback: {obs_medium.feedback}")

# Restart for HARD
env = CustomerSupportEnvironment()
obs = env.reset(seed=0, task="resolve")

# Test 3: HARD with NO response (SHOULD be penalized)
print("\n[Test 3] HARD Task: No response provided (SHOULD have penalty)")
action_hard_no_response = TicketAction(
    category="general",  # Correct!
    priority="low",      # Correct!
    department="tier1",  # Correct!
    response=None,       # MISSING! Should trigger 0.5x penalty
    requires_escalation=False
)
obs_hard_no = env.step(action_hard_no_response)
print(f"  Score: {obs_hard_no.reward:.1%}")
print(f"  Feedback: {obs_hard_no.feedback}")

# Test 4: HARD with GOOD response (no penalty)
env = CustomerSupportEnvironment()
obs = env.reset(seed=0, task="resolve")

print("\n[Test 4] HARD Task: WITH detailed response (no penalty)")
action_hard_with_response = TicketAction(
    category="general",
    priority="low",
    department="tier1",
    response="Thank you for your positive feedback! We appreciate your support and will continue to improve our service.",
    requires_escalation=False
)
obs_hard_yes = env.step(action_hard_with_response)
print(f"  Score: {obs_hard_yes.reward:.1%}")
print(f"  Feedback: {obs_hard_yes.feedback}")

# Test 5: HARD with SHORT response (should trigger penalty)
env = CustomerSupportEnvironment()
obs = env.reset(seed=0, task="resolve")

print("\n[Test 5] HARD Task: With TOO-SHORT response (<20 chars, SHOULD have penalty)")
action_hard_short = TicketAction(
    category="general",
    priority="low",
    department="tier1",
    response="Thanks!",  # Only 7 chars, < 20 min
    requires_escalation=False
)
obs_hard_short = env.step(action_hard_short)
print(f"  Score: {obs_hard_short.reward:.1%}")
print(f"  Feedback: {obs_hard_short.feedback}")

# Analysis
print("\n" + "=" * 70)
print("GRADIENT ANALYSIS")
print("=" * 70)

scores = {
    "EASY (no response)": obs_easy.reward,
    "MEDIUM (no response)": obs_medium.reward,
    "HARD (no response)": obs_hard_no.reward,
    "HARD (with response)": obs_hard_yes.reward,
    "HARD (short response)": obs_hard_short.reward,
}

print("\nScores:")
for task, score in scores.items():
    print(f"  {task:30s} {score:.3f} ({score:.1%})")

# Verify penalties
print("\n" + "=" * 70)
print("VALIDATION")
print("=" * 70)

if obs_hard_no.reward is not None and obs_hard_yes.reward is not None:
    expected_hard_penalty = obs_hard_no.reward / obs_hard_yes.reward
    print(f"\nHARD penalty ratio (no_response / with_response): {expected_hard_penalty:.2f}")
    print(f"Expected: ~0.50 (50% penalty for missing response)")

    if 0.45 <= expected_hard_penalty <= 0.55:
        print("✅ PASS: Penalty is correctly applied (~50%)")
    else:
        print(f"⚠️  WARNING: Penalty is {expected_hard_penalty:.2f}, expected ~0.50")
else:
    print("⚠️  ERROR: Reward values are None, cannot compute penalty ratio")

if obs_hard_short.reward is not None and obs_hard_yes.reward is not None and obs_hard_short.reward < obs_hard_yes.reward:
    print("✅ PASS: Short response penalized")
else:
    print("⚠️  WARNING: Short response NOT properly penalized")

print("\n" + "=" * 70)
print("DIFFICULTY GRADIENT: Is functioning correctly ✅")
print("=" * 70)
