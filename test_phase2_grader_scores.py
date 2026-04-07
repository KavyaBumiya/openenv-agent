#!/usr/bin/env python3
"""Test Phase 2 grader score validation"""
from customer_support_env.graders import ClassifyGrader, RouteGrader, ResolveGrader

print("Testing Phase 2 Grader Scores")
print("="*60)

graders = [ClassifyGrader, RouteGrader, ResolveGrader]

for grader_class in graders:
    result = grader_class.grade({}, {})
    score = result.get('score')
    is_valid = 0 < score < 1
    status = "[OK]" if is_valid else "[FAIL]"
    print(f"{grader_class.__name__:20s}: score={score:.4f}  {status}")
    
    if not is_valid:
        print(f"  ERROR: Score {score} is not strictly between 0 and 1!")
        if score <= 0:
            print(f"  Score is <= 0.0 (should be > 0.0)")
        if score >= 1:
            print(f"  Score is >= 1.0 (should be < 1.0)")

print("="*60)
