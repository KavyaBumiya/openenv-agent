#!/usr/bin/env python3
"""Test OpenAI-compatible integration with the customer support environment."""

import os
import sys

from openai import OpenAI

# Allow running this script directly from tests/ while importing project modules.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ========== CONFIGURE API KEY ==========
# Get from environment variable (secure approach)
api_key = os.getenv("HF_TOKEN")

if not api_key:
    print("ERROR: HF_TOKEN not set")
    print("Set it with: $env:HF_TOKEN='your-key'")
    sys.exit(1)

print("OK - HF_TOKEN loaded from environment\n")

# Initialize OpenAI-compatible client
client = OpenAI(api_key=api_key, base_url=os.getenv("API_BASE_URL", "https://router.huggingface.co/v1"))

# Test 1: Simple completion
print("=" * 60)
print("TEST 1: Simple OpenAI-Compatible API Call")
print("=" * 60)
try:
    response = client.chat.completions.create(
        model=os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct"),
        messages=[
            {"role": "user", "content": "Write a short haiku about AI"}
        ],
        max_tokens=50,
    )
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("LLM returned empty content")
    print("OK - OpenAI-compatible API works!")
    print(f"Response: {content}\n")
except Exception as e:
    print(f"ERROR - {e}\n")
    sys.exit(1)

# Test 2: Environment integration
print("=" * 60)
print("TEST 2: Customer Support Environment")
print("=" * 60)
try:
    from customer_support_env.baseline import extract_json
    from customer_support_env.environment import CustomerSupportEnvironment
    from customer_support_env.models import TicketAction

    env = CustomerSupportEnvironment()
    obs = env.reset(seed=42, task="classify")

    print("OK - Environment initialized")
    print(f"  Ticket: {obs.ticket_id}")
    print(f"  Subject: {obs.subject}")
    print(f"  Task: {obs.task_name}\n")

    # Use the OpenAI-compatible client to classify the ticket
    print("Asking the model to classify the ticket...\n")

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
        model=os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    content = response.choices[0].message.content
    if content is None:
        raise ValueError("LLM returned empty content for JSON response")
    result = extract_json(content)
    print("OK - Model response:")
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
    obs_result, reward, done, info = env.step(action)

    print("OK - Environment step completed")
    print(f"  Reward: {reward}")
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