#!/usr/bin/env python3
"""Test comprehensive score validation"""

from customer_support_env.environment import CustomerSupportEnvironment, _validate_strict_score
from customer_support_env.models import TicketAction

print("="*60)
print("TESTING COMPREHENSIVE SCORE VALIDATION")
print("="*60)

# Test validation function
print("\n1. Testing _validate_strict_score function:")
print(f"   0.0 → {_validate_strict_score(0.0, 'test_zero')}")
print(f"   1.0 → {_validate_strict_score(1.0, 'test_one')}")
print(f"   0.5 → {_validate_strict_score(0.5, 'test_half')}")
print(f"   -0.1 → {_validate_strict_score(-0.1, 'test_negative')}")
print(f"   1.5 → {_validate_strict_score(1.5, 'test_over_one')}")

# Test with environment
print("\n2. Testing environment with all tasks:")
for task in ["classify", "route", "resolve"]:
    print(f"\n   Task: {task}")
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=0, task=task)
    
    # Create appropriate action for task
    if task == "classify":
        action = TicketAction(category='billing', priority='urgent')
    elif task == "route":
        action = TicketAction(category='billing', priority='urgent', department='billing')
    else:  # resolve
        action = TicketAction(
            category='billing',
            priority='urgent',
            department='billing',
            response='Thank you for your inquiry. We will look into this and get back to you soon.'
        )
    
    result_obs, reward, done, info = env.step(action)
    
    print(f"      Reward: {reward:.4f}")
    print(f"      Raw score: {info['raw_score']:.4f}")
    
    # Verify scores are strictly in (0, 1)
    assert 0 < reward < 1, f"Reward {reward} not strictly in (0, 1)"
    assert 0 < info['raw_score'] < 1, f"Raw score {info['raw_score']} not strictly in (0, 1)"
    print(f"      ✓ Scores are valid (strictly between 0 and 1)")

print("\n" + "="*60)
print("✅ ALL VALIDATION TESTS PASSED!")
print("="*60)
