#!/usr/bin/env python3
"""
Integration Tests for Customer Support Environment
==================================================

Simple end-to-end validation that the environment works correctly.

Run before deployment: python tests/test_integration.py
"""

import sys
import os
from typing import Any
from pydantic import ValidationError

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from customer_support_env.environment import CustomerSupportEnvironment
from customer_support_env.models import TicketAction


def test_classify_task():
    """Test CLASSIFY task workflow."""
    print("\n✓ TEST: CLASSIFY task")
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=0, task="classify")
    assert obs.task_name == "classify"
    assert obs.done is False
    
    action = TicketAction(
        category="billing", priority="high", department=None,
        response=None, requires_escalation=False
    )
    result = env.step(action)
    
    assert result.done is True
    assert result.reward is not None
    assert 0.0 <= result.reward <= 1.0
    print(f"  reward={result.reward:.3f}")


def test_route_task():
    """Test ROUTE task workflow."""
    print("\n✓ TEST: ROUTE task")
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=8, task="route")
    assert obs.task_name == "route"
    
    action = TicketAction(
        category="technical", priority="urgent", department="engineering",
        response=None, requires_escalation=True
    )
    result = env.step(action)
    
    assert result.done is True
    assert result.reward is not None
    assert 0.0 <= result.reward <= 1.0
    print(f"  reward={result.reward:.3f}")


def test_resolve_task():
    """Test RESOLVE task workflow."""
    print("\n✓ TEST: RESOLVE task")
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=8, task="resolve")
    assert obs.task_name == "resolve"
    
    action = TicketAction(
        category="technical", priority="urgent", department="engineering",
        response="We're investigating immediately. Update within 2 hours.",
        requires_escalation=True
    )
    result = env.step(action)

    # Hard task supports trajectory steps; first step may not end the episode.
    if not result.done:
        result = env.step(action)
    if not result.done:
        result = env.step(action)

    assert result.done is True
    assert result.reward is not None
    assert 0.0 <= result.reward <= 1.0
    print(f"  reward={result.reward:.3f}")


def test_reward_penalization():
    """Test that wrong answers are penalized."""
    print("\n✓ TEST: Reward penalization for wrong answers")
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=0, task="classify")  # billing/high
    
    # Wrong category
    action = TicketAction(
        category="technical",  # WRONG
        priority="high",
        department=None,
        response=None,
        requires_escalation=False,
    )
    result = env.step(action)
    
    assert result.reward is not None
    assert result.reward < 0.5, f"Wrong answer should be penalized, got {result.reward}"
    print(f"  penalty applied: reward={result.reward:.3f} (was 1.0 with correct answer)")


def test_seeding_reproducibility():
    """Test that same seed produces same ticket."""
    print("\n✓ TEST: Seeding reproducibility")
    
    env1 = CustomerSupportEnvironment()
    obs1 = env1.reset(seed=5, task="classify")
    
    env2 = CustomerSupportEnvironment()
    obs2 = env2.reset(seed=5, task="classify")
    
    assert obs1.ticket_id == obs2.ticket_id
    assert obs1.subject == obs2.subject
    print(f"  seed=5 consistently → {obs1.ticket_id}")


def test_all_seeds_valid():
    """Test that all 30 seeds are valid."""
    print("\n✓ TEST: All 30 seeds valid")
    
    for seed in range(30):
        env = CustomerSupportEnvironment()
        obs = env.reset(seed=seed, task="classify")
        assert obs.ticket_id.startswith("TKT-"), f"Seed {seed} invalid ticket ID"
    
    print(f"  all 30 seeds (0-29) produce valid tickets")


def test_invalid_inputs_rejected():
    """Test that invalid inputs are rejected."""
    print("\n✓ TEST: Invalid inputs rejected")
    
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=0, task="classify")
    
    try:
        # Invalid category
        invalid_category_payload: dict[str, Any] = {
            "category": "invalid_category",
            "priority": "high",
            "department": None,
            "response": None,
            "requires_escalation": False,
        }
        TicketAction.model_validate(invalid_category_payload)
        assert False, "Should have rejected invalid category"
    except ValidationError:
        pass  # Expected
    
    try:
        # Invalid priority
        invalid_priority_payload: dict[str, Any] = {
            "category": "billing",
            "priority": "critical",
            "department": None,
            "response": None,
            "requires_escalation": False,
        }
        TicketAction.model_validate(invalid_priority_payload)
        assert False, "Should have rejected invalid priority"
    except ValidationError:
        pass  # Expected
    
    print(f"  invalid inputs properly rejected")


def test_response_requirement():
    """Test that RESOLVE task requires response."""
    print("\n✓ TEST: RESOLVE task requires response")
    
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=0, task="resolve")
    
    try:
        # Missing response
        action = TicketAction(
            category="billing",
            priority="high",
            department="billing",
            response=None,  # MISSING
            requires_escalation=False,
        )
        env.step(action)
        assert False, "Should have rejected missing response"
    except ValueError:
        pass  # Expected
    
    print(f"  missing response properly rejected")


def main():
    print("=" * 70)
    print("INTEGRATION TESTS: Customer Support Environment")
    print("=" * 70)
    
    tests = [
        test_classify_task,
        test_route_task,
        test_resolve_task,
        test_reward_penalization,
        test_seeding_reproducibility,
        test_all_seeds_valid,
        test_invalid_inputs_rejected,
        test_response_requirement,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("\n✅ ALL INTEGRATION TESTS PASSED!")
        print("Your environment is ready for deployment.")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
