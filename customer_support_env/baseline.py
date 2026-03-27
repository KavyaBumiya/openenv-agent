"""Baseline evaluation: Groq (llama-3.3-70b-versatile) across full dataset per task.

This script proves:
1. The environment is usable by AI agents
2. Score variance is meaningful (not always 0.5)
3. The integration works end-to-end

Reproducibility: seed selects ticket index via modulo mapping.
Requires: GROQ_API_KEY in environment
"""

import json
import sys
import os
import re

try:
    from groq import Groq
except ImportError:
    print("Error: groq package not installed. Install with: pip install groq", file=sys.stderr)
    sys.exit(1)

from customer_support_env.environment import CustomerSupportEnvironment
from customer_support_env.models import TicketAction
from customer_support_env.data import TICKETS


def extract_json(text: str) -> dict:
    """Robustly extract JSON from LLM output, handling markdown fences.
    
    LLMs sometimes wrap JSON in ```json ... ``` blocks.
    This function handles both clean JSON and fenced JSON gracefully.
    """
    if not text:
        raise ValueError("Empty response from LLM")
    
    # First, try the happy path: raw JSON
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Second, strip markdown fences (```json ... ``` or ``` ... ```)
    fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Third, find the outermost JSON object with a greedy search
    brace_match = re.search(r'\{[\s\S]*\}', text)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass
    
    raise ValueError(f"Could not extract valid JSON from: {text[:200]}")


def run_baseline():
    """Run baseline evaluation on all 3 tasks."""
    
    # Check API key
    if not os.getenv("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    env = CustomerSupportEnvironment()
    
    results = {
        "model": "llama-3.3-70b-versatile",
        "provider": "groq",
        "episodes_per_task": len(TICKETS),
        "tasks": {},
    }
    
    for task in ["classify", "route", "resolve"]:
        print(f"\n{'='*60}")
        print(f"Running baseline on task: {task}")
        print(f"{'='*60}")
        
        scores = []
        errors = []
        
        for episode in range(len(TICKETS)):
            try:
                # Reset environment with seed for reproducibility
                # seed=episode means deterministic full-dataset sweep per task
                obs = env.reset(seed=episode, episode_id=f"baseline-{task}-{episode}", task=task)
                
                # Build prompt for the agent
                prompt = _build_prompt(task, obs)
                
                task_temperature = {
                    "classify": 0.1,
                    "route": 0.5,
                    "resolve": 0.7,
                }[task]

                # Call Groq
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    temperature=task_temperature,
                    timeout=30,
                )
                
                # Extract JSON from response
                response_text = response.choices[0].message.content
                if response_text is None:
                    raise ValueError("Groq response content is None")
                action_dict = extract_json(response_text)
                
                # Convert to TicketAction
                action = TicketAction(
                    category=action_dict.get("category", ""),
                    priority=action_dict.get("priority", ""),
                    department=action_dict.get("department"),
                    response=action_dict.get("response"),
                    requires_escalation=action_dict.get("requires_escalation", False),
                )
                
                # Grade action
                step_obs = env.step(action)
                score = step_obs.reward if step_obs.reward is not None else 0.0
                scores.append(score)
                
                print(f"  Episode {episode}: score={score:.3f}")
                
            except ValueError as e:
                print(f"  Episode {episode}: Parse/validation error - {str(e)}")
                errors.append(str(e))
                scores.append(0.0)
            
            except Exception as e:
                print(f"  Episode {episode}: Error - {str(e)}")
                errors.append(str(e))
                scores.append(0.0)
        
        # Compute stats for this task
        task_results = {
            "scores": scores,
            "mean": round(sum(scores) / len(scores), 3),
            "min": round(min(scores), 3),
            "max": round(max(scores), 3),
            "std": round(_compute_std(scores), 3),
        }
        
        if errors:
            task_results["errors"] = len(errors)
        
        results["tasks"][task] = task_results
        
        print(f"\nResults for {task}:")
        print(f"  Mean: {task_results['mean']}")
        print(f"  Min:  {task_results['min']}")
        print(f"  Max:  {task_results['max']}")
        print(f"  Std:  {task_results['std']}")
        if errors:
            print(f"  Errors: {len(errors)}")
    
    # Overall summary
    all_scores = []
    for task_name, task_data in results["tasks"].items():
        all_scores.extend(task_data["scores"])
    
    results["overall"] = {
        "mean": round(sum(all_scores) / len(all_scores), 3),
        "min": round(min(all_scores), 3),
        "max": round(max(all_scores), 3),
    }
    
    print(f"\n{'='*60}")
    print("OVERALL BASELINE RESULTS")
    print(f"{'='*60}")
    print(f"Mean score: {results['overall']['mean']}")
    print(f"Min score:  {results['overall']['min']}")
    print(f"Max score:  {results['overall']['max']}")
    print(f"Score variance: {results['overall']['max'] - results['overall']['min']:.3f}")
    
    # Output JSON for parsing
    # Simplified format: {task_name: mean_score, ...}
    simple_output = {
        task_name: task_data["mean"]
        for task_name, task_data in results["tasks"].items()
    }
    simple_output["_details"] = results  # Include detailed stats
    
    print("\n" + json.dumps(simple_output, indent=2))
    
    return results


def _build_prompt(task: str, obs) -> str:
    """Build the prompt that explains the task to the agent."""
    
    ticket_info = f"""
TICKET INFORMATION:
ID: {obs.ticket_id}
Subject: {obs.subject}
Body: {obs.body}
Customer Tier: {obs.sender_tier}
"""
    
    task_instruction = f"""
TASK: {obs.task_description}

Action Schema (return ONLY valid JSON matching this format):
{obs.action_schema}
"""
    
    policy = ""
    if obs.policy_excerpt:
        policy = f"""
RELEVANT POLICY:
{obs.policy_excerpt}
"""
    
    instructions = f"""
You are an expert customer support routing system. Your job is to read customer tickets and respond with structured JSON.

{ticket_info}
{task_instruction}{policy}

IMPORTANT:
1. Respond ONLY with valid JSON. No other text.
2. All required fields MUST be present.
3. Do not include extra keys beyond the schema.
4. For category, use one of: billing, technical, account, general, or shipping
5. For priority, use one of: low, medium, high, or urgent
6. For department (if required), use one of: tier1, tier2, billing, engineering, or management
7. If writing a response, make it professional, acknowledge the issue, and provide clear next steps.

Analyze the ticket carefully and respond with JSON.
"""
    
    return instructions


def _compute_std(scores: list) -> float:
    """Compute standard deviation of scores."""
    if len(scores) <= 1:
        return 0.0
    
    mean = sum(scores) / len(scores)
    variance = sum((x - mean) ** 2 for x in scores) / len(scores)
    return variance ** 0.5


if __name__ == "__main__":
    run_baseline()
