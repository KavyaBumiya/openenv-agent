#!/usr/bin/env python3
"""Test grader scores exactly as Phase 2 validator would."""

import sys
sys.path.insert(0, '/d/Hackathon')

from customer_support_env.graders import ClassifyGrader, RouteGrader, ResolveGrader

# Test data
test_observations = [
    {
        'ticket_id': 'TKT-001',
        'subject': 'Billing issue',
        'body': 'I was charged twice',
        'sender_tier': 'silver',
        'open_since_hours': 2,
        'sentiment': 'frustrated'
    },
    {
        'ticket_id': 'TKT-002',
        'subject': 'Technical support',
        'body': 'App not working',
        'sender_tier': 'gold',
        'open_since_hours': 24,
        'sentiment': 'angry'
    }
]

test_actions = [
    {
        'category': 'billing',
        'priority': 'high',
        'department': 'billing',
        'requires_escalation': True,
        'response': 'We will investigate this immediately.'
    },
    {
        'category': 'technical',
        'priority': 'urgent',
        'department': 'tier2',
        'requires_escalation': True,
        'response': 'Please try clearing your cache.'
    }
]

print("=" * 70)
print("PHASE 2 GRADER SCORE VALIDATION TEST")
print("=" * 70)

all_valid = True
results = []

for grader_name, grader_class in [
    ('ClassifyGrader', ClassifyGrader),
    ('RouteGrader', RouteGrader),
    ('ResolveGrader', ResolveGrader)
]:
    print(f"\n{grader_name}:")
    print("-" * 70)
    
    for i, (obs, action) in enumerate(zip(test_observations, test_actions)):
        try:
            result = grader_class.grade(obs, action)
            score = result.get('score')
            
            # Validation checks
            is_numeric = isinstance(score, (int, float)) and score == score  # not NaN
            is_positive = score > 0.0
            is_less_than_one = score < 1.0
            is_valid = is_numeric and is_positive and is_less_than_one
            
            status = "✅ PASS" if is_valid else "❌ FAIL"
            results.append({
                'grader': grader_name,
                'test': i+1,
                'score': score,
                'valid': is_valid
            })
            
            print(f"  Test {i+1}: score={score:6.4f} ({status})")
            
            if not is_valid:
                all_valid = False
                if not is_numeric:
                    print(f"    ERROR: score is not numeric or is NaN")
                if not is_positive:
                    print(f"    ERROR: score={score} is NOT > 0.0")
                if not is_less_than_one:
                    print(f"    ERROR: score={score} is NOT < 1.0")
        
        except Exception as e:
            all_valid = False
            print(f"  Test {i+1}: ❌ EXCEPTION: {e}")
            results.append({
                'grader': grader_name,
                'test': i+1,
                'score': None,
                'valid': False,
                'error': str(e)
            })

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

for r in results:
    status = "✅" if r['valid'] else "❌"
    score_str = f"{r['score']:.4f}" if r['score'] is not None else "ERROR"
    print(f"{status} {r['grader']} Test {r['test']}: {score_str}")

print()
if all_valid:
    print("✅ ALL TESTS PASSED - Graders return strictly valid scores!")
else:
    print("❌ SOME TESTS FAILED - Graders have invalid scores!")
    sys.exit(1)
