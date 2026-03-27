#!/usr/bin/env python3
"""Test Groq integration with the customer support environment."""

import os
import sys
from groq import Groq

# ========== CONFIGURE API KEY ==========
# Get from environment variable (secure approach)
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("ERROR: GROQ_API_KEY not set")
    print("Set it with: $env:GROQ_API_KEY='your-key'")
    sys.exit(1)

print("OK - Groq API key loaded from environment\n")

# Initialize Groq client
client = Groq(api_key=api_key)

# Test 1: Simple completion
print("=" * 60)
print("TEST 1: Simple Groq API Call")
print("=" * 60)
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": "Write a short haiku about AI"}
        ],
        max_tokens=50,
    )
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("Groq returned empty content")
    print(f"OK - Groq API works!")
    print(f"Response: {content}\n")
except Exception as e:
    print(f"ERROR - {e}\n")
    sys.exit(1)

# Test 2: Environment integration
print("=" * 60)
print("TEST 2: Customer Support Environment")
print("=" * 60)
try:
    from customer_support_env.environment import CustomerSupportEnvironment
    from customer_support_env.models import TicketAction
    
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=42, task="classify")
    
    print(f"OK - Environment initialized")
    print(f"  Ticket: {obs.ticket_id}")
    print(f"  Subject: {obs.subject}")
    print(f"  Task: {obs.task_name}\n")
    
    # Use Groq to classify the ticket
    print("Asking Groq to classify the ticket...\n")
    
    prompt = f"""Classify this customer support ticket:

Subject: {obs.subject}
Body: {obs.body}
Tier: {obs.sender_tier}

Available categories: billing, technical, account, general, shipping
Priority levels: low, medium, high, urgent

Respond with ONLY valid JSON (no other text):
{{"category": "...", "priority": "..."}}
"""
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    
    from customer_support_env.baseline import extract_json
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("Groq returned empty content for JSON response")
    result = extract_json(content)
    print("OK - Groq response:")
    print(f"  Category: {result['category']}")
    print(f"  Priority: {result['priority']}\n")
    
    # Score the action
    action = TicketAction(
        category=result['category'],
        priority=result['priority'],
        department=None,
        response=None,
        requires_escalation=False
    )
    obs_result = env.step(action)
    
    print(f"OK - Environment step completed")
    print(f"  Reward: {obs_result.reward}")
    print(f"  Feedback: {obs_result.feedback}\n")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Run full baseline
print("=" * 60)
print("TEST 3: Full Baseline Evaluation")
print("=" * 60)
print("This runs one full dataset sweep per task...\n")
print("(This may take 1-2 minutes)\n")

try:
    from customer_support_env.baseline import run_baseline
    run_baseline()
    print("\nOK - Baseline completed successfully!")
except Exception as e:
    print(f"ERROR - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
