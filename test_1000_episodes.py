#!/usr/bin/env python3
"""Test 1000 episodes for out-of-range reward scores"""
import random
from customer_support_env.server.app import app
from fastapi.testclient import TestClient

client = TestClient(app)

print('Testing 1000 random episodes for out-of-range scores...')
out_of_range = []

categories = ['billing', 'technical', 'account', 'general', 'shipping']
priorities = ['low', 'medium', 'high', 'urgent']
deps = ['tier1', 'tier2', 'billing', 'engineering', 'management']

for i in range(1000):
    resp = client.post('/reset', json={})
    session_id = resp.json()['session_id']
    
    action = {
        'session_id': session_id,
        'category': random.choice(categories),
        'priority': random.choice(priorities),
        'department': random.choice(deps),
    }
    
    step_resp = client.post('/step', json=action)
    data = step_resp.json()
    reward = data['reward']
    
    if not (0 < reward < 1):
        out_of_range.append((i, reward))
        
    if (i + 1) % 200 == 0:
        print(f'  Tested {i+1} episodes...')

print()
if out_of_range:
    print(f'ERROR: FOUND {len(out_of_range)} OUT-OF-RANGE SCORES!')
    for idx, score in out_of_range[:10]:
        print(f'  Episode {idx}: reward={score}')
else:
    print('SUCCESS: All 1000 episode rewards are strictly in (0, 1)!')
