#!/usr/bin/env python3
"""Phase 2 Comprehensive Score Validation - All numeric values must be strictly in (0,1)"""
from customer_support_env.server.app import app
from customer_support_env.graders import ClassifyGrader, RouteGrader, ResolveGrader
from fastapi.testclient import TestClient
import json

client = TestClient(app)

print('='*80)
print('PHASE 2 COMPREHENSIVE SCORE VALIDATION')
print('='*80)

# Test 1: Grader scores
print('\n[1] GRADER SCORES (must be strictly in (0, 1))')
print('-'*80)
graders = [
    ('ClassifyGrader', ClassifyGrader),
    ('RouteGrader', RouteGrader),
    ('ResolveGrader', ResolveGrader),
]

grader_valid = True
for name, grader_class in graders:
    result = grader_class.grade({}, {})
    score = result.get('score')
    is_valid = 0 < score < 1
    status = '[OK]' if is_valid else '[FAIL]'
    print(f'{name:20s}: score={score:.4f}  {status}')
    if not is_valid:
        grader_valid = False

# Test 2: Step endpoint rewards (100 episodes)
print('\n[2] STEP ENDPOINT REWARDS (100 episodes)')
print('-'*80)

all_rewards_valid = True
invalid_rewards = []

for i in range(100):
    resp = client.post('/reset', json={})
    session_id = resp.json()['session_id']
    
    action = {
        'session_id': session_id,
        'category': 'billing',
        'priority': 'high',
        'department': 'tier1',
    }
    
    step_resp = client.post('/step', json=action)
    data = step_resp.json()
    reward = data['reward']
    
    if not (0 < reward < 1):
        all_rewards_valid = False
        invalid_rewards.append((i, reward))

if all_rewards_valid:
    print('100 step endpoint rewards: [OK] All strictly in (0, 1)')
else:
    print(f'100 step endpoint rewards: [FAIL] Found {len(invalid_rewards)} invalid')
    for idx, val in invalid_rewards[:5]:
        print(f'  Episode {idx}: reward={val}')

# Test 3: Reward breakdown components
print('\n[3] REWARD BREAKDOWN COMPONENTS (100 episodes)')
print('-'*80)

all_components_valid = True
invalid_components = []

for i in range(100):
    resp = client.post('/reset', json={})
    session_id = resp.json()['session_id']
    
    action = {
        'session_id': session_id,
        'category': 'billing',
        'priority': 'high',
        'department': 'tier1',
    }
    
    step_resp = client.post('/step', json=action)
    data = step_resp.json()
    info = data.get('info', {})
    breakdown = info.get('reward_breakdown', {})
    
    for key, val in breakdown.items():
        if isinstance(val, (int, float)) and key != 'info':
            if not (0 < val < 1):
                all_components_valid = False
                invalid_components.append((i, key, val))

if all_components_valid:
    print('Reward breakdown components: [OK] All strictly in (0, 1)')
else:
    print(f'Reward breakdown components: [FAIL] Found {len(invalid_components)} invalid')
    for idx, key, val in invalid_components[:5]:
        print(f'  Episode {idx}, field "{key}": value={val}')

# Test 4: Raw score values
print('\n[4] RAW SCORE VALUES IN INFO (100 episodes)')
print('-'*80)

all_raw_scores_valid = True
invalid_raw_scores = []

for i in range(100):
    resp = client.post('/reset', json={})
    session_id = resp.json()['session_id']
    
    action = {
        'session_id': session_id,
        'category': 'billing',
        'priority': 'high',
        'department': 'tier1',
    }
    
    step_resp = client.post('/step', json=action)
    data = step_resp.json()
    info = data.get('info', {})
    raw_score = info.get('raw_score')
    
    if raw_score is not None:
        if not (0 < raw_score < 1):
            all_raw_scores_valid = False
            invalid_raw_scores.append((i, raw_score))

if all_raw_scores_valid:
    print('Raw scores in info: [OK] All strictly in (0, 1)')
else:
    print(f'Raw scores in info: [FAIL] Found {len(invalid_raw_scores)} invalid')
    for idx, val in invalid_raw_scores[:5]:
        print(f'  Episode {idx}: raw_score={val}')

# Final summary
print('\n' + '='*80)
print('PHASE 2 VALIDATION SUMMARY')
print('='*80)

all_valid = grader_valid and all_rewards_valid and all_components_valid and all_raw_scores_valid

results = [
    ('Grader scores', grader_valid),
    ('Step rewards', all_rewards_valid),
    ('Breakdown components', all_components_valid),
    ('Raw scores', all_raw_scores_valid),
]

for name, valid in results:
    status = '[PASS]' if valid else '[FAIL]'
    print(f'{name:30s}: {status}')

print('='*80)
if all_valid:
    print('[SUCCESS] Phase 2 validation is ready - all scores strictly in (0, 1)!')
else:
    print('[FAILURE] Some scores are out of range - fix required!')
