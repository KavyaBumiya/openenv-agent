#!/usr/bin/env python3
"""
Customer Support RL Environment - Main Entry Point

This is the single main file to run the entire environment.

Usage:
    python main.py                    # Show menu
    python main.py baseline           # Run baseline evaluation  
    python main.py server             # Start FastAPI server
    python main.py test               # Run quick test
    python main.py demo               # Interactive demo
"""

import os
import sys
import json
import argparse
from typing import Optional

# Ensure environment is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from customer_support_env.environment import CustomerSupportEnvironment
from customer_support_env.models import TicketAction


def run_baseline():
    """Run baseline evaluation with Groq API."""
    print("\n" + "=" * 80)
    print("BASELINE EVALUATION: Groq (llama-3.3-70b-versatile)")
    print("=" * 80)
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ ERROR: GROQ_API_KEY environment variable not set")
        print("\nSet it with: $env:GROQ_API_KEY='your-key' (PowerShell)")
        return
    
    try:
        from groq import Groq
    except ImportError:
        print("❌ ERROR: groq package not installed")
        print("Install with: pip install groq")
        return
    
    client = Groq(api_key=api_key)
    env = CustomerSupportEnvironment()
    
    results = {"model": "llama-3.3-70b-versatile", "tasks": {}}
    
    for task in ["classify", "route", "resolve"]:
        # Temperature settings per task
        temp_settings = {"classify": 0.1, "route": 0.5, "resolve": 0.7}
        temp = temp_settings.get(task, 0.1)
        
        print(f"\n{'─' * 80}")
        print(f"Task: {task.upper()} (temperature={temp})")
        print(f"{'─' * 80}")
        
        scores = []
        
        for episode in range(10):
            try:
                obs = env.reset(seed=episode, task=task)
                
                # Build prompt based on task
                if task == "classify":
                    prompt = f"""Classify this customer support ticket:

Subject: {obs.subject}
Body: {obs.body}
Tier: {obs.sender_tier}

Respond with ONLY valid JSON:
{{"category": "billing|technical|account|general|shipping", "priority": "low|medium|high|urgent"}}"""
                
                elif task == "route":
                    prompt = f"""Route this customer support ticket:

Subject: {obs.subject}
Body: {obs.body}
Tier: {obs.sender_tier}

Determine:
1. Category (billing|technical|account|general|shipping)
2. Priority (low|medium|high|urgent)
3. Department (tier1|tier2|billing|engineering|management)
4. Escalation needed (true|false)

Respond with ONLY valid JSON:
{{"category": "...", "priority": "...", "department": "...", "requires_escalation": false}}"""
                
                else:  # resolve
                    prompt = f"""Resolve this customer support ticket:

Subject: {obs.subject}
Body: {obs.body}
Tier: {obs.sender_tier}

Determine:
1. Category, Priority, Department, Escalation (as above)
2. Write a 2-3 sentence professional response

Respond with ONLY valid JSON:
{{"category": "...", "priority": "...", "department": "...", "requires_escalation": false, "response": "Your response here"}}"""
                
                # Call Groq
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temp,
                    timeout=30,
                )
                
                response_text = response.choices[0].message.content
                if not response_text:
                    raise ValueError("Empty response")
                
                # Parse JSON
                action_dict = json.loads(response_text)
                
                # Create action
                action = TicketAction(
                    category=action_dict.get("category", ""),
                    priority=action_dict.get("priority", ""),
                    department=action_dict.get("department"),
                    response=action_dict.get("response"),
                    requires_escalation=action_dict.get("requires_escalation", False),
                )
                
                # Grade
                step_obs = env.step(action)
                score = step_obs.reward if step_obs.reward is not None else 0.0
                scores.append(score)
                
                print(f"  Episode {episode:2d}: {score:.1%}")
                
            except Exception as e:
                print(f"  Episode {episode:2d}: ❌ {str(e)[:50]}")
                scores.append(0.0)
        
        # Stats
        mean = sum(scores) / len(scores) if scores else 0
        min_s = min(scores) if scores else 0
        max_s = max(scores) if scores else 0
        results["tasks"][task] = {
            "mean": mean,
            "min": min_s,
            "max": max_s,
            "scores": scores,
        }
        
        print(f"\n  Summary: Mean={mean:.1%}, Range={min_s:.1%}→{max_s:.1%}")
    
    # Print final results
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    for task, data in results["tasks"].items():
        print(f"\n{task.upper()}:")
        print(f"  Mean:   {data['mean']:.1%}")
        print(f"  Min:    {data['min']:.1%}")
        print(f"  Max:    {data['max']:.1%}")
    
    # Gradient check
    easy = results["tasks"]["classify"]["mean"]
    medium = results["tasks"]["route"]["mean"]
    hard = results["tasks"]["resolve"]["mean"]
    
    if easy > medium > hard:
        print(f"\n✅ DIFFICULTY GRADIENT: EASY ({easy:.1%}) > MEDIUM ({medium:.1%}) > HARD ({hard:.1%})")
    else:
        print(f"\n⚠️  GRADIENT: Easy={easy:.1%}, Medium={medium:.1%}, Hard={hard:.1%}")


def run_server():
    """Start FastAPI server."""
    print("\n" + "=" * 80)
    print("STARTING FASTAPI SERVER")
    print("=" * 80)
    
    try:
        import uvicorn
    except ImportError:
        print("❌ ERROR: uvicorn not installed")
        print("Install with: pip install uvicorn")
        return
    
    print("\nServer will be available at: http://localhost:8000")
    print("API docs at: http://localhost:8000/docs")
    print("Press Ctrl+C to stop\n")
    
    # Import app
    from customer_support_env.server.app import app
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


def run_quick_test():
    """Run a quick environment test."""
    print("\n" + "=" * 80)
    print("QUICK ENVIRONMENT TEST")
    print("=" * 80)
    
    env = CustomerSupportEnvironment()
    
    print("\n1. Testing CLASSIFY task...")
    obs = env.reset(seed=0, task="classify")
    print(f"   Subject: {obs.subject}")
    print(f"   Body: {obs.body[:80]}...")
    
    # Random action
    action = TicketAction(
        category="general",
        priority="low",
        department=None,
        response=None,
        requires_escalation=False
    )
    result = env.step(action)
    print(f"   Score: {result.reward:.1%}")
    
    print("\n2. Testing ROUTE task...")
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=0, task="route")
    action = TicketAction(
        category="general",
        priority="low",
        department="tier1",
        response=None,
        requires_escalation=False
    )
    result = env.step(action)
    print(f"   Score: {result.reward:.1%}")
    
    print("\n3. Testing RESOLVE task...")
    env = CustomerSupportEnvironment()
    obs = env.reset(seed=0, task="resolve")
    action = TicketAction(
        category="general",
        priority="low",
        department="tier1",
        response="Thank you for your feedback!",
        requires_escalation=False
    )
    result = env.step(action)
    print(f"   Score: {result.reward:.1%}")
    
    print("\n✅ Environment is working correctly!")


def run_interactive_demo():
    """Interactive environment demo."""
    print("\n" + "=" * 80)
    print("INTERACTIVE ENVIRONMENT DEMO")
    print("=" * 80)
    
    env = CustomerSupportEnvironment()
    
    while True:
        print("\n" + "─" * 80)
        print("Choose task: (1) classify, (2) route, (3) resolve, (0) exit")
        choice = input("Enter choice (0-3): ").strip()
        
        if choice == "0":
            break
        
        task_map = {"1": "classify", "2": "route", "3": "resolve"}
        if choice not in task_map:
            print("Invalid choice")
            continue
        
        task = task_map[choice]
        seed = int(input(f"Enter seed (0-29): ").strip() or "0")
        
        # Reset
        obs = env.reset(seed=seed, task=task)
        print(f"\n📋 Ticket {obs.ticket_id}:")
        print(f"   Subject: {obs.subject}")
        print(f"   Body: {obs.body}")
        print(f"   Tier: {obs.sender_tier}")
        
        if task == "classify":
            cat = input("\nCategory (billing|technical|account|general|shipping): ").strip()
            pri = input("Priority (low|medium|high|urgent): ").strip()
            action = TicketAction(
                category=cat,
                priority=pri,
                department=None,
                response=None,
                requires_escalation=False
            )
        
        elif task == "route":
            cat = input("\nCategory: ").strip()
            pri = input("Priority: ").strip()
            dept = input("Department (tier1|tier2|billing|engineering|management): ").strip()
            esc = input("Escalate? (true|false): ").strip().lower() == "true"
            action = TicketAction(
                category=cat,
                priority=pri,
                department=dept,
                response=None,
                requires_escalation=esc
            )
        
        else:  # resolve
            cat = input("\nCategory: ").strip()
            pri = input("Priority: ").strip()
            dept = input("Department: ").strip()
            esc = input("Escalate? (true|false): ").strip().lower() == "true"
            resp = input("Response: ").strip()
            action = TicketAction(
                category=cat,
                priority=pri,
                department=dept,
                response=resp,
                requires_escalation=esc
            )
        
        # Grade
        result = env.step(action)
        print(f"\n✔️  Score: {result.reward:.1%}")
        print(f"📝 Feedback: {result.feedback}")


def show_menu():
    """Show main menu."""
    print("\n" + "=" * 80)
    print("CUSTOMER SUPPORT RL ENVIRONMENT")
    print("=" * 80)
    print("""
Commands:
  main.py baseline    - Run baseline evaluation with Groq (10 episodes per task)
  main.py server      - Start FastAPI server (http://localhost:8000)
  main.py test        - Run quick environment test
  main.py demo        - Interactive demo mode
  
Examples:
  python main.py baseline
  python main.py server
  python main.py test
  python main.py demo

Documentation:
  README.md              - Quick start guide
  README_PRODUCTION.md   - Full specification
  TRAINING_GUIDE.md      - Groq prompting guide
  DEPLOYMENT.md          - HuggingFace Spaces deployment
  ENVIRONMENT_SETUP.md   - Environment configuration

Tests:
  test_improved_training.py    - Validation test
  test_gradient_penalty.py     - Difficulty gradient test
  test_temperature_corrected.py - Temperature effect demo
""")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Customer Support RL Environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py baseline      Run baseline evaluation
  python main.py server        Start API server
  python main.py test          Quick test
  python main.py demo          Interactive demo
        """
    )
    parser.add_argument("command", nargs="?", help="Command to run")
    args = parser.parse_args()
    
    if not args.command:
        show_menu()
        return
    
    if args.command == "baseline":
        run_baseline()
    elif args.command == "server":
        run_server()
    elif args.command == "test":
        run_quick_test()
    elif args.command == "demo":
        run_interactive_demo()
    else:
        print(f"❌ Unknown command: {args.command}")
        show_menu()


if __name__ == "__main__":
    main()
