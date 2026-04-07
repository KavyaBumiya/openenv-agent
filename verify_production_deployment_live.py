#!/usr/bin/env python3
"""Production Deployment Verification"""
import json
import requests
from datetime import datetime

SPACE_URL = "https://kavyabumiya-customer-support-env.hf.space"

print("="*80)
print(f"PRODUCTION DEPLOYMENT VERIFICATION")
print(f"Space: {SPACE_URL}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

tests_passed = 0
tests_failed = 0

# Test 1: Health
print("\n[1] Health Check")
try:
    r = requests.get(f"{SPACE_URL}/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data.get('status') == 'healthy'
    print(f"    [OK] Status: {data['status']}")
    tests_passed += 1
except Exception as e:
    print(f"    [FAIL] {e}")
    tests_failed += 1

# Test 2: Tasks
print("\n[2] Tasks Endpoint")
try:
    r = requests.get(f"{SPACE_URL}/tasks", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    task_names = [t.get('name') or t.get('id') for t in data]
    print(f"    [OK] {len(data)} tasks: {', '.join(task_names)}")
    tests_passed += 1
except Exception as e:
    print(f"    [FAIL] {e}")
    tests_failed += 1

# Test 3: Reset (New Episode)
print("\n[3] Reset Endpoint (New Episode)")
try:
    r = requests.post(f"{SPACE_URL}/reset", json={}, timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert 'session_id' in data
    assert 'observation' in data
    obs = data['observation']
    assert 'ticket_id' in obs
    session_id = data['session_id']
    print(f"    [OK] Session created: {session_id[:8]}...")
    print(f"         Observation fields: {len(obs)} fields")
    tests_passed += 1
except Exception as e:
    print(f"    [FAIL] {e}")
    tests_failed += 1
    session_id = None

# Test 4: Step (Action)
if session_id:
    print("\n[4] Step Endpoint (Submit Action)")
    try:
        action = {
            'session_id': session_id,
            'category': 'billing',
            'priority': 'high',
            'department': 'billing',
        }
        r = requests.post(f"{SPACE_URL}/step", json=action, timeout=5)
        assert r.status_code == 200
        data = r.json()
        reward = data.get('reward')
        assert reward is not None
        assert 0 < reward < 1, f"Reward {reward} not strictly in (0, 1)"
        print(f"    [OK] Action processed")
        print(f"         Reward: {reward:.4f}")
        print(f"         Done: {data.get('done')}")
        tests_passed += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        tests_failed += 1

# Test 5: Grader Info
print("\n[5] Grader Endpoint")
try:
    r = requests.get(f"{SPACE_URL}/grader", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert 'graders' in data or len(str(data)) > 10
    print(f"    [OK] Grader info available")
    tests_passed += 1
except Exception as e:
    print(f"    [FAIL] {e}")
    tests_failed += 1

# Summary
print("\n" + "="*80)
print(f"RESULTS: {tests_passed} passed, {tests_failed} failed")
if tests_failed == 0:
    print("[SUCCESS] Production deployment is operational and ready!")
else:
    print(f"[WARNING] {tests_failed} test(s) failed - check space status")
print("="*80)
