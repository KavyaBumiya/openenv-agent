#!/usr/bin/env python3
"""Test Groq on three difficulty levels: EASY, MEDIUM, HARD.

This demonstrates progressive task complexity:
- EASY: Predict category + priority (basic classification)
- MEDIUM: + department + escalation flag (routing logic)
- HARD: + professional response (resolution)

All test on the SAME ticket so you can see how Groq handles increasing complexity.
"""

import os
import sys
import json
from groq import Groq

# ========== SETUP ==========
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("ERROR: GROQ_API_KEY not set")
    sys.exit(1)

print("OK - Groq API key loaded from environment\n")
client = Groq(api_key=api_key)

# Use a real ticket
from customer_support_env.environment import CustomerSupportEnvironment
from customer_support_env.models import TicketAction

env = CustomerSupportEnvironment()
obs = env.reset(seed=42, task="classify")

print("=" * 70)
print("TESTING GROQ ON THREE DIFFICULTY LEVELS")
print("=" * 70)
print(f"\nTicket ID: {obs.ticket_id}")
print(f"Subject: {obs.subject}")
print(f"Body: {obs.body}\n")

# ========== EASY TASK ==========
print("\n" + "=" * 70)
print("EASY TASK: Predict CATEGORY + PRIORITY")
print("=" * 70)

prompt_easy = f"""You are a customer support classifier.

Read this ticket and classify it:

SUBJECT: {obs.subject}
BODY: {obs.body}
CUSTOMER TIER: {obs.sender_tier}

Respond with ONLY valid JSON (no other text):
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
    print(f"\n✓ EASY Result:")
    print(f"  Category: {easy_result['category']}")
    print(f"  Priority: {easy_result['priority']}")
    
    # Score it
    action_easy = TicketAction(
        category=easy_result['category'],
        priority=easy_result['priority'],
        department=None,
        response=None,
        requires_escalation=False
    )
    obs_easy = env.step(action_easy)
    print(f"  Score: {obs_easy.reward:.1%}")
    print(f"  Feedback: {obs_easy.feedback}")
    
except Exception as e:
    print(f"\n✗ EASY Failed: {e}")
    sys.exit(1)

# ========== MEDIUM TASK ==========
print("\n" + "=" * 70)
print("MEDIUM TASK: +DEPARTMENT + ESCALATION")
print("=" * 70)

prompt_medium = f"""You are a customer support router.

Read this ticket and determine routing:

SUBJECT: {obs.subject}
BODY: {obs.body}
CUSTOMER TIER: {obs.sender_tier}

Respond with ONLY valid JSON (no other text):
{{"category": "...", "priority": "...", "department": "...", "requires_escalation": true/false}}

Categories: billing, technical, account, general, shipping
Priorities: low, medium, high, urgent
Departments: tier1, tier2, billing, engineering, management

ROUTING LOGIC:
- tier1: general questions, simple troubleshooting, standard refunds
- tier2: complex technical issues, account problems
- billing: payment issues, invoicing, subscriptions
- engineering: feature requests, bugs, performance
- management: escalated complaints, retention at risk
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
    print(f"\n✓ MEDIUM Result:")
    print(f"  Category: {medium_result['category']}")
    print(f"  Priority: {medium_result['priority']}")
    print(f"  Department: {medium_result['department']}")
    print(f"  Requires Escalation: {medium_result['requires_escalation']}")
    
    # Score it
    action_medium = TicketAction(
        category=medium_result['category'],
        priority=medium_result['priority'],
        department=medium_result['department'],
        response=None,
        requires_escalation=medium_result['requires_escalation']
    )
    obs_medium = env.step(action_medium)
    print(f"  Score: {obs_medium.reward:.1%}")
    print(f"  Feedback: {obs_medium.feedback}")
    
except Exception as e:
    print(f"\n✗ MEDIUM Failed: {e}")
    sys.exit(1)

# ========== HARD TASK ==========
print("\n" + "=" * 70)
print("HARD TASK: +PROFESSIONAL RESPONSE")
print("=" * 70)

prompt_hard = f"""You are an expert customer support agent.

Read this ticket and respond professionally:

SUBJECT: {obs.subject}
BODY: {obs.body}
CUSTOMER TIER: {obs.sender_tier}

Respond with ONLY valid JSON (no other text):
{{"category": "...", "priority": "...", "department": "...", "requires_escalation": true/false, "response": "..."}}

Categories: billing, technical, account, general, shipping
Priorities: low, medium, high, urgent
Departments: tier1, tier2, billing, engineering, management

RESPONSE GUIDELINES:
- Acknowledge their issue and frustration
- Show you understand the business impact
- Provide clear next steps
- End with empathy
- 2-4 sentences max
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
    print(f"\n✓ HARD Result:")
    print(f"  Category: {hard_result['category']}")
    print(f"  Priority: {hard_result['priority']}")
    print(f"  Department: {hard_result['department']}")
    print(f"  Requires Escalation: {hard_result['requires_escalation']}")
    print(f"  Response:\n    \"{hard_result['response']}\"")
    
    # Score it
    action_hard = TicketAction(
        category=hard_result['category'],
        priority=hard_result['priority'],
        department=hard_result['department'],
        response=hard_result['response'],
        requires_escalation=hard_result['requires_escalation']
    )
    obs_hard = env.step(action_hard)
    print(f"  Score: {obs_hard.reward:.1%}")
    print(f"  Feedback: {obs_hard.feedback}")
    
except Exception as e:
    print(f"\n✗ HARD Failed: {e}")
    sys.exit(1)

# ========== COMPARISON ==========
print("\n" + "=" * 70)
print("DIFFICULTY COMPARISON")
print("=" * 70)
print(f"""
EASY (Category + Priority):
  Score: {obs_easy.reward:.1%}

MEDIUM (+ Department + Escalation):
  Score: {obs_medium.reward:.1%}

HARD (+ Response):
  Score: {obs_hard.reward:.1%}

Insight:
- EASY tests basic classification (should be high score)
- MEDIUM tests routing logic (should be medium-high score)
- HARD tests empathy + completeness (should be lower score, hardest task)
""")

print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)
