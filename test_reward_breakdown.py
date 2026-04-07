#!/usr/bin/env python3
"""Test reward breakdown components are all strictly in (0, 1)"""
from customer_support_env.server.app import app
from fastapi.testclient import TestClient

client = TestClient(app)

print('Testing reward breakdown components...')
print('='*70)

all_valid = True
for i in range(5):
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
    info = data.get('info', {})
    breakdown = info.get('reward_breakdown', {})
    
    print(f'Episode {i}:')
    print(f'  Reward (value): {reward:.4f} - {"OK" if 0 < reward < 1 else "BAD"}')
    
    if breakdown:
        for key, val in breakdown.items():
            if isinstance(val, (int, float)):
                is_valid = 0 < val < 1
                status = "OK" if is_valid else "BAD"
                if not is_valid:
                    all_valid = False
                print(f'    {key:30s}: {val:.4f}  [{status}]')
    print()

print('='*70)
if all_valid:
    print('SUCCESS: All reward components are strictly in (0, 1)!')
else:
    print('ERROR: Some reward components are out of range!')
