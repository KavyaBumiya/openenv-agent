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
import logging

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load from .env file in current directory
except ImportError:
    pass  # dotenv not installed, skip

from customer_support_env.environment import CustomerSupportEnvironment
from customer_support_env.models import TicketAction
from customer_support_env.data import TICKETS

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def extract_json(text: str, expected_keys: list = None) -> dict:
    """Robustly extract JSON from LLM output with validation.
    
    Args:
        text: Raw LLM response text
        expected_keys: List of required keys in JSON (e.g., ["category", "priority"])
    
    Returns:
        Validated JSON dictionary
    
    Raises:
        ValueError: If JSON cannot be extracted or validated
    """
    if not text:
        raise ValueError("Empty response from LLM")
    
    text = text.strip()
    errors = []
    
    # Strategy 1: Direct JSON parse (fast path)
    try:
        data = json.loads(text)
        _validate_json_structure(data, expected_keys)
        logger.debug("Successfully extracted JSON via direct parse")
        return data
    except (json.JSONDecodeError, ValueError) as e:
        errors.append(f"Direct parse: {e}")
        logger.debug(f"Direct parse failed: {e}")
    
    # Strategy 2: Markdown code fence (```json ... ```)
    fence_match = re.search(r'```(?:json)?\s+([\s\S]*?)\s+```', text)
    if fence_match:
        try:
            data = json.loads(fence_match.group(1))
            _validate_json_structure(data, expected_keys)
            logger.debug("Successfully extracted JSON via markdown fence")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            errors.append(f"Markdown fence: {e}")
            logger.debug(f"Fence parse failed: {e}")
    
    # Strategy 3: Find JSON objects (non-greedy, try each match)
    # Use non-greedy matching to avoid grabbing too much text
    for match in re.finditer(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', text):
        try:
            extracted_text = match.group()
            data = json.loads(extracted_text)
            _validate_json_structure(data, expected_keys)
            logger.debug(f"Successfully extracted JSON from object search")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Object search attempt failed: {e}")
            continue
    
    # All strategies failed
    error_summary = "; ".join(errors)
    error_msg = f"Could not extract valid JSON from LLM response. Strategies tried: {error_summary}"
    logger.error(f"{error_msg}\nOriginal response: {text[:300]}...")
    raise ValueError(error_msg)


def _validate_json_structure(data: dict, required_keys: list = None) -> None:
    """Validate that extracted JSON has correct structure.
    
    Args:
        data: Dictionary to validate
        required_keys: List of keys that must exist
    
    Raises:
        ValueError: If validation fails
    """
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")
    
    if required_keys:
        missing = set(required_keys) - set(data.keys())
        if missing:
            raise ValueError(f"Missing required keys: {missing}")
    
    # Validate values (check for null/empty)
    for key, value in data.items():
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"Field '{key}' cannot be empty string")
        elif value is None:
            raise ValueError(f"Field '{key}' cannot be null")


def run_baseline(mode="official"):
    """Run baseline evaluation on all 3 tasks.
    
    Args:
        mode: "official" (low temp, reproducible) or "training" (variable temp for exploration)
    
    Official mode: temperature=0.1 for all tasks (deterministic, reproducible scores for benchmarking)
    Training mode: task-specific temps (0.1/0.5/0.7 for difficulty-based exploration)
    """

    try:
        from groq import Groq
    except ImportError:
        print("Error: groq package not installed. Install with: pip install groq", file=sys.stderr)
        sys.exit(1)
    
    # Check API key
    if not os.getenv("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    env = CustomerSupportEnvironment()
    
    # Set temperature strategy based on mode
    if mode == "official":
        # Benchmark mode: low temperature for reproducibility
        temp_strategy = {
            "classify": 0.1,
            "route": 0.1,
            "resolve": 0.1,
        }
        mode_label = "OFFICIAL BENCHMARK (temperature=0.1 all tasks)"
    elif mode == "training":
        # Training/exploration mode: task-specific temps for variance
        temp_strategy = {
            "classify": 0.1,
            "route": 0.5,
            "resolve": 0.7,
        }
        mode_label = "TRAINING MODE (variable temperature by task)"
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'official' or 'training'")
    
    results = {
        "model": "llama-3.3-70b-versatile",
        "provider": "groq",
        "mode": mode,
        "temperature_strategy": temp_strategy,
        "episodes_per_task": len(TICKETS),
        "tasks": {},
    }
    
    print(f"\n{'='*60}")
    print(f"BASELINE EVALUATION: {mode_label}")
    print(f"{'='*60}\n")
    
    for task in ["classify", "route", "resolve"]:
        print(f"\n{'='*60}")
        print(f"Running {mode} baseline on task: {task}")
        print(f"Temperature: {temp_strategy[task]}")
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
                
                task_temperature = temp_strategy[task]

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
                
                # Expected keys for this task
                expected_keys_map = {
                    "classify": ["category", "priority"],
                    "route": ["category", "priority", "department"],
                    "resolve": ["category", "priority", "department", "response"],
                }
                expected_keys = expected_keys_map.get(task, [])
                
                # Extract and validate JSON
                action_dict = extract_json(response_text, expected_keys=expected_keys)
                logger.debug(f"Episode {episode}: Extracted action - {action_dict}")
                
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
    # Note: We only output simple results here to ensure regex JSON extraction works reliably
    
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
    import argparse
    
    parser = argparse.ArgumentParser(description="Run baseline evaluation")
    parser.add_argument(
        "--mode",
        choices=["official", "training"],
        default="official",
        help="Benchmark mode (reproducible, low-temp) or training mode (exploratory, variable-temp)"
    )
    args = parser.parse_args()
    
    run_baseline(mode=args.mode)
