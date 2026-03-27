#!/usr/bin/env python3
"""Test Groq variability with temperature settings.

Shows that:
- temperature=0.0 → Same output every time (BAD for testing)
- temperature=0.7 → Different outputs each time (GOOD for testing)
"""

import os
import sys
from groq import Groq

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("ERROR: GROQ_API_KEY not set")
    sys.exit(1)

client = Groq(api_key=api_key)

print("=" * 80)
print("GROQ VARIABILITY TEST")
print("=" * 80)

ticket = {
    "subject": "Order never arrived, need replacement",
    "body": "I ordered a phone on March 15 and it still hasn't arrived. Can you help?",
    "sender_tier": "standard"
}

# Test 1: Temperature = 0.0 (Deterministic)
print("\n[Test 1] Temperature = 0.0 (Completely Deterministic)")
print("-" * 80)

responses_zero = []
for i in range(3):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"""Classify this support ticket:

Subject: {ticket['subject']}
Body: {ticket['body']}

Respond with ONLY valid JSON:
{{"category": "billing|technical|account|general|shipping", "priority": "low|medium|high|urgent"}}"""
        }],
        temperature=0.0,  # DETERMINISTIC
    )
    
    content = response.choices[0].message.content
    responses_zero.append(content)
    print(f"  Run {i+1}: {content}")

print(f"\n  All same? {responses_zero[0] == responses_zero[1] == responses_zero[2]}")

# Test 2: Temperature = 0.7 (Variable)
print("\n[Test 2] Temperature = 0.7 (Variable/Random)")
print("-" * 80)

responses_var = []
for i in range(3):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"""Classify this support ticket:

Subject: {ticket['subject']}
Body: {ticket['body']}

Respond with ONLY valid JSON:
{{"category": "billing|technical|account|general|shipping", "priority": "low|medium|high|urgent"}}"""
        }],
        temperature=0.7,  # VARIABLE
    )
    
    content = response.choices[0].message.content
    responses_var.append(content)
    print(f"  Run {i+1}: {content}")

# Count unique responses
unique_var = len(set(responses_var))
print(f"\n  Unique responses: {unique_var}/3")
print(f"  All same? {responses_var[0] == responses_var[1] == responses_var[2]}")

# Test 3: Temperature = 0.3 (Balanced)
print("\n[Test 3] Temperature = 0.3 (Balanced)")
print("-" * 80)

responses_balanced = []
for i in range(3):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"""Classify this support ticket:

Subject: {ticket['subject']}
Body: {ticket['body']}

Respond with ONLY valid JSON:
{{"category": "billing|technical|account|general|shipping", "priority": "low|medium|high|urgent"}}"""
        }],
        temperature=0.3,  # BALANCED
    )
    
    content = response.choices[0].message.content
    responses_balanced.append(content)
    print(f"  Run {i+1}: {content}")

unique_balanced = len(set(responses_balanced))
print(f"\n  Unique responses: {unique_balanced}/3")

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

print(f"""
🔴 temperature=0.0 (Current):
   - Always same response ✓
   - No variability ✗
   - NOT suitable for testing

🟢 temperature=0.3-0.7 (Recommended):
   - Some variability
   - Still mostly correct
   - GOOD for testing environment

⚠️  ISSUE: Tests are using temperature=0.0, so you get identical scores!

📊 SOLUTION:
   1. Use temperature=0.3-0.5 for EASY tasks (mostly same)
   2. Use temperature=0.5-0.7 for MEDIUM/HARD tasks (more variation)
   3. Run tests multiple times to see score distribution

🎯 NEXT: Modify test_improved_training.py to use variable temperature
""")
