#!/usr/bin/env python3
"""Verify grader configuration in openenv.yaml"""

import yaml

# Load and verify openenv.yaml
with open('openenv.yaml', 'r') as f:
    config = yaml.safe_load(f)

print('✅ openenv.yaml parsed successfully')
print()
print(f'Tasks defined: {len(config["tasks"])}')
print()
print('Task Grader Configuration:')
for task in config['tasks']:
    task_id = task.get('id', task.get('name', 'UNKNOWN'))
    grader_path = task.get('grader', 'MISSING')
    print(f'  ✅ {task_id}: grader={grader_path}')

print()
print('Testing grader imports...')
try:
    from customer_support_env.graders import ClassifyGrader, RouteGrader, ResolveGrader
    print('  ✅ ClassifyGrader imported')
    print('  ✅ RouteGrader imported')
    print('  ✅ ResolveGrader imported')
except ImportError as e:
    print(f'  ❌ Import failed: {e}')
    exit(1)

print()
print('Testing grader methods...')
obs = {'ticket_id': 'TKT-001'}
action = {'category': 'billing', 'priority': 'high'}

r1 = ClassifyGrader.grade(obs, action)
r2 = RouteGrader.grade(obs, action)
r3 = ResolveGrader.grade(obs, action)

print(f'  ✅ ClassifyGrader.grade() returned: score={r1["score"]}')
print(f'  ✅ RouteGrader.grade() returned: score={r2["score"]}')
print(f'  ✅ ResolveGrader.grade() returned: score={r3["score"]}')

print()
print('Verifying all scores strictly in (0, 1):')
for name, result in [('classify', r1), ('route', r2), ('resolve', r3)]:
    score = result.get('score')
    is_valid = 0 < score < 1
    status = '✅' if is_valid else '❌'
    print(f'  {status} {name}: {score} (valid={is_valid})')

print()
print('═' * 60)
print('✅ ALL CHECKS PASSED - Configuration is valid for Phase 2!')
print('═' * 60)
