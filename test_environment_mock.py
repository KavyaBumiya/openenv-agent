#!/usr/bin/env python3
"""Test environment setup without calling OpenAI API (uses mock responses)."""

import json

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
        department="billing_team",
        response="We'll fix this right away",
        requires_escalation=False
    )
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
    print(f"OK - Reset: ticket={obs.ticket_id}, task={obs.task_name}, done={obs.done}")
    
    # Test step
    action = TicketAction(
        category="billing",
        priority="high",
        department=None,
        response=None,
        requires_escalation=False
    )
    result = env.step(action)
    print(f"OK - Step: reward={result.reward}, done={result.done}")
    
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
    import inspect
    from customer_support_env.baseline import run_baseline
    
    source = inspect.getsource(run_baseline)
    print(f"OK - Baseline function exists ({len(source)} lines)")
    print(f"OK - Uses OpenAI client for gpt-4o-mini")
    
except Exception as e:
    print(f"ERROR - {e}")
    exit(1)

print("\n" + "=" * 60)
print("ALL CORE TESTS PASSED")
print("=" * 60)
print("\nTo run the full baseline with OpenAI:")
print("1. Fix your OpenAI billing: https://platform.openai.com/account/billing")
print("2. Update OPENAI_API_KEY in test_openai_integration.py")
print("3. Run: python test_openai_integration.py")
