#!/usr/bin/env python3
"""Test environment setup without calling external LLM APIs (mock mode)."""

import json
import os
import sys

# Allow running this script directly from tests/ while importing project modules.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print("=" * 60)
print("TESTING CUSTOMER SUPPORT ENVIRONMENT (Mock Mode)")
print("=" * 60)

# Test 1: Models
print("\n[TEST 1] Models")
try:
    from customer_support_env.models import TicketAction, TicketObservation, TicketState
    
    action = TicketAction(
        category="billing",
        priority="high",
        department="billing",
        response="We'll fix this right away",
        requires_escalation=False
    )
    assert action.department == "billing"
    print(f"OK - TicketAction: {action.category}, {action.priority}")
    
    obs = TicketObservation(
        done=False,
        reward=None,
        ticket_id="TKT-001",
        subject="Test subject",
        body="Test body",
        sender_tier="premium",
        previous_tickets=0,
        task_name="classify",
        task_description="Classify this ticket",
        action_schema="{}",
        policy_excerpt="",
        feedback=""
    )
    print(f"OK - TicketObservation: {obs.ticket_id}, task={obs.task_name}")
    
    state = TicketState(
        episode_id="ep-001",
        step_count=0,
        task_name="classify",
        difficulty="easy"
    )
    print(f"OK - TicketState: {state.episode_id}")
    
except Exception as e:
    print(f"ERROR - {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 2: Dataset
print("\n[TEST 2] Dataset")
try:
    from customer_support_env.data import TICKETS
    
    print(f"OK - Loaded {len(TICKETS)} tickets")
    ticket = TICKETS[0]
    print(f"OK - Sample ticket: {ticket['id']} - {ticket['subject']}")
    
except Exception as e:
    print(f"ERROR - {e}")
    exit(1)

# Test 3: Environment
print("\n[TEST 3] Environment")
try:
    from customer_support_env.environment import CustomerSupportEnvironment
    
    env = CustomerSupportEnvironment()
    print(f"OK - Environment created")
    
    # Test reset
    obs = env.reset(seed=42, task="classify")
    assert obs.done is False, "reset() should return done=False"
    print(f"OK - Reset: ticket={obs.ticket_id}, task={obs.task_name}, done={obs.done}")
    
    # Test step
    action = TicketAction(
        category="billing",
        priority="high",
        department=None,
        response=None,
        requires_escalation=False
    )
    result_obs, reward, done, info = env.step(action)
    assert done is True, "step() should return done=True for single-turn episodes"
    assert reward is not None, "step() should return a reward"
    print(f"OK - Step: reward={reward}, done={done}")
    
except Exception as e:
    print(f"ERROR - {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 4: Server
print("\n[TEST 4] FastAPI Server")
try:
    from customer_support_env.server.app import app as fastapi_app
    
    print(f"OK - FastAPI app initialized")
    print(f"OK - Routes: {len(fastapi_app.routes)}")
    
    # List routes
    for route in fastapi_app.routes[:5]:
        route_path = getattr(route, "path", str(route))
        print(f"  - {route_path}")
    
except Exception as e:
    print(f"ERROR - {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 5: Baseline structure (mock)
print("\n[TEST 5] Baseline Structure")
try:
    baseline_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "customer_support_env",
        "baseline.py",
    )
    with open(baseline_path, "r", encoding="utf-8") as f:
        source = f.read()

    assert "def run_baseline" in source
    assert "extract_json" in source
    print(f"OK - Baseline module present ({len(source.splitlines())} lines)")
    print("OK - Uses OpenAI-compatible baseline pipeline")
    
except Exception as e:
    print(f"ERROR - {e}")
    exit(1)

print("\n" + "=" * 60)
print("ALL CORE TESTS PASSED")
print("=" * 60)
print("\nTo run the full baseline:")
print("1. Set HF_TOKEN in your environment")
print("2. Run: python tests/test_live_integration.py")
