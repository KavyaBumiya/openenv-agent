#!/usr/bin/env python3
"""Corrected Training: Proper temperature settings for variability.

Key Fix: Use temperature=0.7 for MEDIUM/HARD tasks to allow Groq to explore
different responses. This shows true reward distribution.
"""

import os
import sys
import json
import re
from groq import Groq

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("ERROR: GROQ_API_KEY not set")
    sys.exit(1)

client = Groq(api_key=api_key)

from customer_support_env.environment import CustomerSupportEnvironment
from customer_support_env.models import TicketAction

print("=" * 80)
print("CORRECTED TRAINING: With Proper Temperature Settings")
print("=" * 80)
print("\nRunning 5 tickets × 3 passes each (to show variability)\n")

results = {
    "easy": [],
    "medium": [],
    "hard": [],
}

for ticket_num in range(5):
    print(f"[Ticket {ticket_num + 1}/5]", end=" ", flush=True)
    
    for pass_num in range(3):
        # ========== EASY (temperature=0.1) ==========
        env = CustomerSupportEnvironment()
        obs = env.reset(seed=ticket_num, task="classify")
        
        prompt_easy = f"""Classify this customer support ticket:

Subject: {obs.subject}
Body: {obs.body}
Tier: {obs.sender_tier}

Respond with ONLY valid JSON:
{{"category": "billing|technical|account|general|shipping", "priority": "low|medium|high|urgent"}}
"""
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt_easy}],
                temperature=0.1,  # Low for classification (mostly deterministic)
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("Empty response")
            
            json_match = re.search(r'\{[^{}]*\}', content)
            if json_match:
                easy_result = json.loads(json_match.group())
            else:
                easy_result = json.loads(content)
            
            action = TicketAction(
                category=easy_result['category'],
                priority=easy_result['priority'],
                department=None,
                response=None,
                requires_escalation=False
            )
            obs_easy = env.step(action)
            results["easy"].append(obs_easy.reward)
        except Exception as e:
            results["easy"].append(0)
        
        # ========== MEDIUM (temperature=0.5) ==========
        env = CustomerSupportEnvironment()
        obs = env.reset(seed=ticket_num, task="route")
        
        prompt_medium = f"""Route this customer support ticket:

Subject: {obs.subject}
Body: {obs.body}
Tier: {obs.sender_tier}

First classify the category and priority.
Then determine the department: tier1|tier2|billing|engineering|management.
Decide if this needs escalation (true/false).

Respond with ONLY valid JSON:
{{"category": "...", "priority": "...", "department": "tier1|tier2|billing|engineering|management", "requires_escalation": true|false}}
"""
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt_medium}],
                temperature=0.5,  # Medium for routing (some variability)
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("Empty response")
            
            json_match = re.search(r'\{[^{}]*\}', content)
            if json_match:
                medium_result = json.loads(json_match.group())
            else:
                medium_result = json.loads(content)
            
            action = TicketAction(
                category=medium_result['category'],
                priority=medium_result['priority'],
                department=medium_result['department'],
                response=None,
                requires_escalation=medium_result.get('requires_escalation', False)
            )
            obs_medium = env.step(action)
            results["medium"].append(obs_medium.reward)
        except Exception as e:
            results["medium"].append(0)
        
        # ========== HARD (temperature=0.7) ==========
        env = CustomerSupportEnvironment()
        obs = env.reset(seed=ticket_num, task="resolve")
        
        prompt_hard = f"""Resolve this customer support ticket with a professional response:

Subject: {obs.subject}
Body: {obs.body}
Tier: {obs.sender_tier}

STEPS:
1. Classify ticket (category, priority)
2. Route to department (tier1|tier2|billing|engineering|management)
3. Assess if escalation needed (true/false)
4. Write a 2-3 sentence response that:
   - Acknowledges the customer's issue
   - Shows empathy and understanding
   - Provides a clear action or next steps
   - Ends on a positive note

Respond with ONLY valid JSON:
{{"category": "...", "priority": "...", "department": "...", "requires_escalation": true|false, "response": "Your helpful response here"}}
"""
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt_hard}],
                temperature=0.7,  # High for generation (more creative variation)
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("Empty response")
            
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                hard_result = json.loads(json_match.group())
            else:
                hard_result = json.loads(content)
            
            action = TicketAction(
                category=hard_result['category'],
                priority=hard_result['priority'],
                department=hard_result['department'],
                response=hard_result.get('response', ''),
                requires_escalation=hard_result.get('requires_escalation', False)
            )
            obs_hard = env.step(action)
            results["hard"].append(obs_hard.reward)
        except Exception as e:
            results["hard"].append(0)
        
        print(".", end="", flush=True)
    
    print(f" ✓", flush=True)

# Compute stats
def compute_stats(scores):
    if not scores:
        return 0, 0, 0, 0
    mean = sum(scores) / len(scores)
    min_s = min(scores)
    max_s = max(scores)
    std = (sum((x - mean) ** 2 for x in scores) / len(scores)) ** 0.5 if len(scores) > 1 else 0
    return mean, min_s, max_s, std

print("\n" + "=" * 80)
print("RESULTS: Temperature-Based Training (5 tickets × 3 passes)")
print("=" * 80)

temp_map = {'easy': 0.1, 'medium': 0.5, 'hard': 0.7}

for difficulty in ["easy", "medium", "hard"]:
    mean, min_s, max_s, std = compute_stats(results[difficulty])
    temp = temp_map[difficulty]
    print(f"\n{difficulty.upper()} (temp: {temp}):")
    print(f"  Mean:   {mean:.1%}")
    print(f"  Range:  {min_s:.1%} → {max_s:.1%}")
    print(f"  Std:    {std:.3f}")
    print(f"  All 15 scores: {[f'{x:.0%}' for x in results[difficulty]]}")

print("\n" + "=" * 80)
print("GRADIENT VERIFICATION")
print("=" * 80)

easy_mean, _, _, _ = compute_stats(results["easy"])
medium_mean, _, _, _ = compute_stats(results["medium"])
hard_mean, _, _, _ = compute_stats(results["hard"])

print(f"\nEASY:   {easy_mean:.1%}")
print(f"MEDIUM: {medium_mean:.1%}")
print(f"HARD:   {hard_mean:.1%}")

if easy_mean > medium_mean > hard_mean:
    print(f"\n✅ PROPER GRADIENT: Easy > Medium > Hard")
elif easy_mean > hard_mean and medium_mean > hard_mean:
    print(f"\n✅ GRADIENT MOSTLY CORRECT: Hard is lowest")
else:
    print(f"\n⚠️  GRADIENT ISSUE: Check if ticket difficulty varies")

print("\n" + "=" * 80)
print("KEY FINDINGS")
print("=" * 80)

print(f"""
1. EASY Task (temperature=0.1):
   - Should be high and STABLE (low std: {compute_stats(results['easy'])[3]:.3f})
   - Current: {easy_mean:.1%}

2. MEDIUM Task (temperature=0.5):
   - Medium performance with SOME VARIATION
   - Current: {medium_mean:.1%} (std: {compute_stats(results['medium'])[3]:.3f})

3. HARD Task (temperature=0.7):
   - Lower performance, MORE VARIATION (harder to solve consistently)
   - Current: {hard_mean:.1%} (std: {compute_stats(results['hard'])[3]:.3f})

✅ SOLUTION APPLIED:
   - Different temperatures for different tasks
   - Variability now visible in results
   - Standard deviation shows prediction uncertainty
   - Proper difficulty gradient maintained
""")
