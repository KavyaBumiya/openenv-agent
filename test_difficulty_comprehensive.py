#!/usr/bin/env python3
"""Comprehensive difficulty test: Run EASY/MEDIUM/HARD on 10 tickets.

Shows how Groq performance degrades with increasing task complexity.
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
print("COMPREHENSIVE DIFFICULTY TEST: 10 tickets × 3 difficulty levels")
print("=" * 70)

results = {
    "easy": [],
    "medium": [],
    "hard": []
}

for seed in range(10):
    print(f"\n[Ticket {seed + 1}/10]", end=" ", flush=True)
    
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=seed, task="classify")
    
    # ========== EASY ==========
    prompt_easy = f"""Classify this ticket:

SUBJECT: {obs.subject}
BODY: {obs.body}
TIER: {obs.sender_tier}

Respond ONLY with JSON:
{{"category": "...", "priority": "..."}}

Categories: billing, technical, account, general, shipping
Priorities: low, medium, high, urgent
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_easy}],
            temperature=0.1,
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Groq returned empty response")
        easy_result = json.loads(content)
        action = TicketAction(
            category=easy_result['category'],
            priority=easy_result['priority'],
            department=None,
            response=None,
            requires_escalation=False
        )
        obs_easy = env.step(action)
        easy_score = obs_easy.reward
        results["easy"].append(easy_score)
        print(f"EASY: {easy_score:.0%}", end=" | ", flush=True)
    except Exception as e:
        print(f"EASY: ERROR", end=" | ", flush=True)
        results["easy"].append(0)
    
    # ========== MEDIUM ==========
    prompt_medium = f"""Route this ticket:

SUBJECT: {obs.subject}
BODY: {obs.body}
TIER: {obs.sender_tier}

Respond ONLY with JSON:
{{"category": "...", "priority": "...", "department": "...", "requires_escalation": false}}

Categories: billing, technical, account, general, shipping
Priorities: low, medium, high, urgent
Departments: tier1, tier2, billing, engineering, management
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_medium}],
            temperature=0.1,
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Groq returned empty response")
        medium_result = json.loads(content)
        action = TicketAction(
            category=medium_result['category'],
            priority=medium_result['priority'],
            department=medium_result['department'],
            response=None,
            requires_escalation=medium_result['requires_escalation']
        )
        obs_medium = env.step(action)
        medium_score = obs_medium.reward
        results["medium"].append(medium_score)
        print(f"MEDIUM: {medium_score:.0%}", end=" | ", flush=True)
    except Exception as e:
        print(f"MEDIUM: ERROR", end=" | ", flush=True)
        results["medium"].append(0)
    
    # ========== HARD ==========
    prompt_hard = f"""Fully resolve this ticket:

SUBJECT: {obs.subject}
BODY: {obs.body}
TIER: {obs.sender_tier}

Respond ONLY with JSON:
{{"category": "...", "priority": "...", "department": "...", "requires_escalation": false, "response": "..."}}

Categories: billing, technical, account, general, shipping
Priorities: low, medium, high, urgent
Departments: tier1, tier2, billing, engineering, management
Response: 2-4 sentences, professional, empathetic, with clear next steps.
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_hard}],
            temperature=0.1,
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Groq returned empty response")
        hard_result = json.loads(content)
        action = TicketAction(
            category=hard_result['category'],
            priority=hard_result['priority'],
            department=hard_result['department'],
            response=hard_result['response'],
            requires_escalation=hard_result['requires_escalation']
        )
        obs_hard = env.step(action)
        hard_score = obs_hard.reward
        results["hard"].append(hard_score)
        print(f"HARD: {hard_score:.0%}", flush=True)
    except Exception as e:
        print(f"HARD: ERROR", flush=True)
        results["hard"].append(0)

# Compute stats
def compute_stats(scores):
    if not scores:
        return 0, 0, 0, 0
    mean = sum(scores) / len(scores)
    min_score = min(scores)
    max_score = max(scores)
    std = (sum((x - mean) ** 2 for x in scores) / len(scores)) ** 0.5 if len(scores) > 1 else 0
    return mean, min_score, max_score, std

print("\n" + "=" * 70)
print("RESULTS SUMMARY")
print("=" * 70)

for difficulty in ["easy", "medium", "hard"]:
    mean, min_s, max_s, std = compute_stats(results[difficulty])
    print(f"\n{difficulty.upper()}:")
    print(f"  Mean:   {mean:.1%}")
    print(f"  Min:    {min_s:.1%}")
    print(f"  Max:    {max_s:.1%}")
    print(f"  Std:    {std:.3f}")
    print(f"  Scores: {[f'{x:.0%}' for x in results[difficulty]]}")

print("\n" + "=" * 70)
print("INSIGHT: Score degradation shows task complexity hierarchy")
print("=" * 70)
