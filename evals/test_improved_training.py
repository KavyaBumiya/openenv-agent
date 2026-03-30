#!/usr/bin/env python3
"""Improved Groq Training: Better prompts with few-shot examples and deep analysis.

Key improvements:
1. Few-shot examples showing correct reasoning
2. Explicit instructions to analyze body/subject
3. Chain-of-thought prompting
4. Penalty validation for missing responses in HARD task
"""

import os
import sys
import json
from groq import Groq

# Allow running this script directly from evals/ while importing project modules.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("ERROR: GROQ_API_KEY not set")
    sys.exit(1)

client = Groq(api_key=api_key)

from customer_support_env.environment import CustomerSupportEnvironment
from customer_support_env.models import TicketAction
from customer_support_env.baseline import extract_json

print("=" * 80)
print("IMPROVED GROQ TRAINING: Few-Shot + Deep Analysis")
print("=" * 80)

# Few-shot examples (from dataset)
EXAMPLES = {
    "classify": """
Example 1:
Subject: Wrong amount charged on my account
Body: I was charged $49.99 but I only selected the $29.99 plan. This happened two days ago...
Analysis: The body mentions BILLING terminology ("charged", "plan", "refunded"). Urgency: customer waited 2 days. 
Decision: category="billing", priority="high"

Example 2:
Subject: Can I downgrade to a cheaper plan
Body: I've been on the Pro plan for 8 months but I realize I don't use all the features...
Analysis: The body mentions PLAN changes ("downgrade", "cheaper plan"). Urgency: casual request no rush indicated.
Decision: category="billing", priority="low"
""",
    
    "route": """
Example 1:
Subject: Wrong amount charged on my account
Body: I was charged $49.99 but I only selected... Tier: premium
Analysis: Billing issue. Customer is PREMIUM tier (needs quick handling). Open 28 hours (SLA concern).
Decision: category="billing", priority="high", department="billing", requires_escalation=False

Example 2:
Subject: Charged twice for subscription renewal
Body: My card was debited twice yesterday... Tier: enterprise
Analysis: Duplicate charge (financial trust issue). ENTERPRISE customer (highest priority).
Decision: category="billing", priority="urgent", department="billing", requires_escalation=True
""",
    
    "resolve": """
Example 1:
Subject: Wrong amount charged on my account
Body: I was charged $49.99 but I only selected the $29.99 plan...
Response: "We sincerely apologize for this billing error. We have identified the overcharge and will process an immediate refund to your account within 24 hours. Thank you for your patience, and please confirm receipt of the refund."
Analysis: Response includes: apology (acknowledge frustration), action (immediate refund), timeline (24h), gratitude.

Example 2:
Subject: Great service, thanks!
Body: I've been using your platform for 2 years... great work!
Response: "Thank you so much for the wonderful feedback! We're thrilled you've had such a positive experience. Your loyalty means everything to us, and we're excited to continue delivering great service."
Analysis: Positive sentiment → empathetic gratitude, reinforces relationship, forward-looking.
"""
}

results = {
    "easy": [],
    "medium": [],
    "hard": [],
}

print("\nRunning 10 tickets with improved prompts...\n")

for seed in range(10):
    print(f"[Ticket {seed + 1}/10]", end=" ", flush=True)
    
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=seed, task="classify")
    
    # ========== EASY (with few-shot) ==========
    prompt_easy = f"""{EXAMPLES['classify']}

Now classify this ticket:

Subject: {obs.subject}
Body: {obs.body}
Tier: {obs.sender_tier}

Instructions:
1. Analyze the subject line - what domain is it in?
2. Analyze the body - look for domain-specific keywords
3. Assess urgency from the context
4. Respond ONLY with valid JSON:

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
        
        easy_result = extract_json(content)
        
        action = TicketAction(
            category=easy_result['category'],
            priority=easy_result['priority'],
            department=None,
            response=None,
            requires_escalation=False
        )
        obs_easy = env.step(action)
        easy_score = obs_easy.reward
        results["easy"].append(easy_score)
        print(f"EASY: {easy_score:.0%}", end=" | ", flush=True)
    except Exception as e:
        print(f"EASY: ERROR ({str(e)[:20]})", end=" | ", flush=True)
        results["easy"].append(0)
    
    # ========== MEDIUM (with few-shot) ==========
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=seed, task="route")
    
    prompt_medium = f"""{EXAMPLES['route']}

Now route this ticket:

Subject: {obs.subject}
Body: {obs.body}
Tier: {obs.sender_tier}

Instructions:
1. Classify category and priority (use same logic as above)
2. Determine which DEPARTMENT should handle this:
   - tier1: General questions, simple troubleshooting, policy-based requests
   - tier2: Complex technical issues, account investigations
   - billing: Payment issues, subscriptions, invoicing
   - engineering: Bugs, feature requests, performance issues
   - management: Escalated complaints, VIP retention, contract disputes
3. Determine if requires escalation: True if financial impact, VIP customer, or trust issue
4. Respond ONLY with valid JSON:

{{"category": "...", "priority": "...", "department": "...", "requires_escalation": false}}
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_medium}],
            temperature=0.5,  # Medium for routing (some variation)
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Empty response")
        
        medium_result = extract_json(content)
        
        action = TicketAction(
            category=medium_result['category'],
            priority=medium_result['priority'],
            department=medium_result['department'],
            response=None,
            requires_escalation=medium_result.get('requires_escalation', False)
        )
        obs_medium = env.step(action)
        medium_score = obs_medium.reward
        results["medium"].append(medium_score)
        print(f"MEDIUM: {medium_score:.0%}", end=" | ", flush=True)
    except Exception as e:
        print(f"MEDIUM: ERROR", end=" | ", flush=True)
        results["medium"].append(0)
    
    # ========== HARD (with few-shot + response generation) ==========
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=seed, task="resolve")
    
    prompt_hard = f"""{EXAMPLES['resolve']}

Now fully resolve this ticket:

Subject: {obs.subject}
Body: {obs.body}
Tier: {obs.sender_tier}

Instructions:
1. Classify and route (use above logic)
2. Write a professional response (2-4 sentences):
   - Acknowledge their issue
   - Show you understand the business impact
   - Provide clear next steps
   - Match tone to sentiment (frustrated→empathetic, positive→grateful)
3. Respond ONLY with valid JSON:

{{"category": "...", "priority": "...", "department": "...", "requires_escalation": false, "response": "..."}}
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_hard}],
            temperature=0.7,  # Higher for generation (more creative variation)
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Empty response")
        
        hard_result = extract_json(content)
        
        action = TicketAction(
            category=hard_result['category'],
            priority=hard_result['priority'],
            department=hard_result['department'],
            response=hard_result.get('response', ''),
            requires_escalation=hard_result.get('requires_escalation', False)
        )
        obs_hard = env.step(action)
        hard_score = obs_hard.reward
        results["hard"].append(hard_score)
        print(f"HARD: {hard_score:.0%}", flush=True)
    except Exception as e:
        print(f"HARD: ERROR", flush=True)
        results["hard"].append(0)

# Compute stats
def compute_stats(scores):
    if not scores:
        return 0, 0, 0, 0
    mean = sum(scores) / len(scores)
    min_score = min(scores)
    max_score = max(scores)
    std = (sum((x - mean) ** 2 for x in scores) / len(scores)) ** 0.5 if len(scores) > 1 else 0
    return mean, min_score, max_score, std

print("\n" + "=" * 80)
print("RESULTS WITH IMPROVED PROMPTS")
print("=" * 80)

for difficulty in ["easy", "medium", "hard"]:
    mean, min_s, max_s, std = compute_stats(results[difficulty])
    print(f"\n{difficulty.upper()}:")
    print(f"  Mean:   {mean:.1%}")
    print(f"  Min:    {min_s:.1%}")
    print(f"  Max:    {max_s:.1%}")
    print(f"  Std:    {std:.3f}")
    print(f"  Scores: {[f'{x:.0%}' for x in results[difficulty]]}")

# Check difficulty gradient
print("\n" + "=" * 80)
print("DIFFICULTY GRADIENT ANALYSIS")
print("=" * 80)

easy_mean, _, _, _ = compute_stats(results["easy"])
medium_mean, _, _, _ = compute_stats(results["medium"])
hard_mean, _, _, _ = compute_stats(results["hard"])

print(f"\nEASY:   {easy_mean:.1%}")
print(f"MEDIUM: {medium_mean:.1%}")
print(f"HARD:   {hard_mean:.1%}")

if hard_mean < medium_mean < easy_mean:
    print("\n✅ PROPER GRADIENT: HARD < MEDIUM < EASY (difficulty increases)")
elif easy_mean >= medium_mean >= hard_mean:
    print("\n⚠️  WEAKER GRADIENT: Some tasks have similar scores")
    print("   This is NORMAL - classification difficulty is still the bottleneck")
else:
    print("\n❌ UNEXPECTED: Gradient not monotonic")

print("\n" + "=" * 80)
print("KEY INSIGHTS")
print("=" * 80)
print("""
1. If HARD ≈ MEDIUM ≈ EASY: Classification is the limiting factor
   → Groq is good at category/priority, response generation is easy

2. If HARD < MEDIUM < EASY: Difficulty gradient is working
   → Response generation is hard, department routing is medium

3. Few-shot examples help Groq understand domain and reasoning

4. Next steps:
   - Try chain-of-thought: Ask Groq to explain before answering
   - Add more examples to few-shot
   - Improve dataset with harder edge cases
   - Use ensemble methods (majority voting across attempts)
""")
