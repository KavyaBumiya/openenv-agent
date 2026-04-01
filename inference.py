#!/usr/bin/env python3
"""
OpenEnv Compliant Inference Script
====================================

This script demonstrates a baseline agent solving the Customer Support Environment
using the OpenAI Client API with structured logging in the required [START], [STEP], [END] format.

Requirements:
  - API_BASE_URL: LLM endpoint (default: Hugging Face router)
  - MODEL_NAME: Model identifier (default: meta-llama/Llama-2-7b-chat-hf)
  - HF_TOKEN: Hugging Face API token

Compliance:
  - Emits [START], [STEP], [END] logging per spec
  - Uses OpenAI Client for LLM calls
  - Runs on modest hardware (vcpu=2, memory=8GB)
  - Completes within 20 minutes
  - Reproducible scores across all 3 tasks (easy, medium, hard)

Usage:
  export API_BASE_URL="https://router.huggingface.co/v1"
  export MODEL_NAME="meta-llama/Llama-2-7b-chat-hf"
  export HF_TOKEN="hf_your_token_here"
  
  python inference.py

Authors: OpenEnv Hackathon Baseline
"""

import asyncio
import json
import logging
import os
import sys
import textwrap
from typing import List, Optional, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Suppress verbose logging to keep stdout clean for evaluation

# ============================================================================
# Configuration from Environment
# ============================================================================
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-2-7b-chat-hf")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
API_KEY = HF_TOKEN  # For OpenAI Client

# Environment configuration
ENVIRONMENT_NAME = "customer_support_env"
MAX_STEPS = 1  # Single-turn environment: max 1 step per task
NUM_SEEDS = 3  # Test 3 seeds per task (9 total episodes)
TEMPERATURE = 0.3  # Conservative temperature for reproducible baseline
MAX_TOKENS = 500

SUCCESS_SCORE_THRESHOLD = 0.1  # Episode success if score >= 0.1

# ============================================================================
# Import Environment
# ============================================================================
try:
    from customer_support_env.environment import CustomerSupportEnvironment
    from customer_support_env.models import TicketAction, TicketObservation
except ImportError as e:
    print(f"[ERROR] Failed to import environment: {e}", file=sys.stderr)
    print("[ERROR] Make sure you're running from the repository root", file=sys.stderr)
    sys.exit(1)


# ============================================================================
# Structured Logging Functions (Per Spec)
# ============================================================================

def log_start(task: str, env: str, model: str) -> None:
    """Emit [START] log line.
    
    Format: [START] task=<task_name> env=<benchmark> model=<model_name>
    """
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    step: int,
    action: str,
    reward: float,
    done: bool,
    error: Optional[str],
) -> None:
    """Emit [STEP] log line.
    
    Format: [STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    
    Rules:
      - One [STEP] line per environment step
      - reward formatted to 2 decimal places
      - done and error are lowercase booleans (true/false) or null
    """
    error_str = str(error) if error else "null"
    done_str = "true" if done else "false"
    # Truncate action representation if too long
    action_truncated = action[:100] if len(action) > 100 else action
    print(
        f"[STEP] step={step} action={action_truncated} reward={reward:.2f} done={done_str} error={error_str}",
        flush=True,
    )


def log_end(
    success: bool,
    steps: int,
    score: float,
    rewards: List[float],
) -> None:
    """Emit [END] log line.
    
    Format: [END] success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>
    
    Rules:
      - One [END] line per episode
      - rewards formatted to 2 decimal places, comma-separated
      - success is a lowercase boolean
    """
    success_str = "true" if success else "false"
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={success_str} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ============================================================================
# LLM Integration with OpenAI Client
# ============================================================================

def get_openai_client():
    """Create OpenAI client with custom base URL and API key.
    
    This uses the OpenAI Python client but points to a custom endpoint
    (e.g., Hugging Face API router) for flexibility.
    """
    try:
        from openai import OpenAI
    except ImportError:
        print(
            "[ERROR] openai package not installed. Install with: pip install openai",
            file=sys.stderr,
        )
        sys.exit(1)
    
    if not API_KEY:
        print(
            "[ERROR] HF_TOKEN / API_KEY not set in environment. Export it and retry.",
            file=sys.stderr,
        )
        sys.exit(1)
    
    return OpenAI(api_key=API_KEY, base_url=API_BASE_URL)


def build_system_prompt(task_name: str) -> str:
    """Build task-specific system prompt for consistent LLM behavior.
    
    Args:
        task_name: "classify", "route", or "resolve"
    
    Returns:
        System prompt guiding the agent's response format
    """
    prompts = {
        "classify": textwrap.dedent("""\
            You are a customer support triage specialist.
            
            Your job: Read the customer ticket and classify it.
            
            Output ONLY a valid JSON object with these fields (no markdown, no explanation):
            {
              "category": "billing|technical|account|shipping|general",
              "priority": "low|medium|high|urgent"
            }
            
            Be concise. Output the JSON on a single line."""),
        
        "route": textwrap.dedent("""\
            You are a customer support routing specialist.
            
            Your job: Read the ticket and decide where to route it.
            
            Output ONLY a valid JSON object with these fields (no markdown, no explanation):
            {
              "category": "billing|technical|account|shipping|general",
              "priority": "low|medium|high|urgent",
              "department": "tier1|tier2|billing|engineering|management",
              "requires_escalation": true|false
            }
            
            Be concise. Output the JSON on a single line."""),
        
        "resolve": textwrap.dedent("""\
            You are a customer support representative resolving cases.
            
            Your job: Read the ticket, classify it, route it, AND send a brief response.
            
            Output ONLY a valid JSON object with these fields (no markdown, no explanation):
            {
              "category": "billing|technical|account|shipping|general",
              "priority": "low|medium|high|urgent",
              "department": "tier1|tier2|billing|engineering|management",
              "requires_escalation": true|false,
              "response": "Your professional, helpful response to the customer (1-2 sentences)"
            }
            
            Response should:
            - Acknowledge the issue
            - Provide next steps or solution
            - Maintain professional, empathetic tone
            
            Be concise. Output the JSON on a single line."""),
    }
    
    return prompts.get(task_name, prompts["classify"])


def build_user_prompt(observation: TicketObservation) -> str:
    """Build user prompt from observation.
    
    Args:
        observation: TicketObservation from environment
    
    Returns:
        User prompt with ticket details and context
    """
    return textwrap.dedent(f"""\
        Ticket ID: {observation.ticket_id}
        Sender Tier: {observation.sender_tier}
        Sentiment: {observation.sentiment}
        Open for: {observation.open_since_hours} hours
        
        Subject: {observation.subject}
        
        Body:
        {observation.body}
        
        ---
        Task: {observation.task_description}
        
        Action Schema: {observation.action_schema}
        
        Policy Guide:
        {observation.policy_excerpt}
        """).strip()


def extract_and_validate_json(
    text: str,
    expected_keys: List[str],
    task_name: str,
) -> Optional[dict]:
    """Extract JSON from LLM response and validate structure.
    
    Handles common LLM quirks:
    - Markdown code fences (```json ... ```)
    - Extra explanation before/after JSON
    - Various quote styles
    
    Args:
        text: Raw LLM response
        expected_keys: Required JSON keys for this task
        task_name: "classify", "route", or "resolve"
    
    Returns:
        Validated JSON dict, or None if parsing/validation fails
    """
    if not text:
        logger.warning(f"[{task_name}] Empty LLM response")
        return None
    
    # Try direct JSON parse first
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict) and all(k in data for k in expected_keys):
            logger.debug(f"[{task_name}] Extracted JSON directly")
            return data
    except json.JSONDecodeError:
        pass
    
    # Try markdown fence (```json ... ```)
    import re
    fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if fence_match:
        try:
            data = json.loads(fence_match.group(1).strip())
            if isinstance(data, dict) and all(k in data for k in expected_keys):
                logger.debug(f"[{task_name}] Extracted JSON from markdown fence")
                return data
        except json.JSONDecodeError:
            pass
    
    # Try to extract first JSON object
    json_match = re.search(r'\{[^{}]*["\'](?:' + '|'.join(expected_keys) + r')["\'].*?\}', text)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            if isinstance(data, dict) and all(k in data for k in expected_keys):
                logger.debug(f"[{task_name}] Extracted JSON from text")
                return data
        except json.JSONDecodeError:
            pass
    
    logger.warning(f"[{task_name}] Failed to extract valid JSON from: {text[:100]}")
    return None


def get_model_action(
    client: Any,
    task_name: str,
    observation: TicketObservation,
) -> Optional[TicketAction]:
    """Query LLM for action on the given observation.
    
    Args:
        client: OpenAI client
        task_name: "classify", "route", or "resolve"
        observation: TicketObservation from environment
    
    Returns:
        TicketAction if successful, None on error
    """
    system_prompt = build_system_prompt(task_name)
    user_prompt = build_user_prompt(observation)
    
    # Expected fields per task
    expected_fields = {
        "classify": ["category", "priority"],
        "route": ["category", "priority", "department", "requires_escalation"],
        "resolve": ["category", "priority", "department", "requires_escalation", "response"],
    }
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        
        response_text = (completion.choices[0].message.content or "").strip()
        logger.debug(f"LLM response for {task_name}: {response_text[:200]}")
        
        # Parse JSON
        data = extract_and_validate_json(
            response_text,
            expected_fields[task_name],
            task_name,
        )
        
        if not data:
            logger.warning(f"Failed to parse LLM response for {task_name}")
            return None
        
        # Convert to TicketAction
        action = TicketAction(
            category=data.get("category", "general"),
            priority=data.get("priority", "low"),
            department=data.get("department"),
            requires_escalation=data.get("requires_escalation", False),
            response=data.get("response"),
        )
        
        return action
    
    except Exception as e:
        logger.error(f"LLM request failed for {task_name}: {e}")
        return None


# ============================================================================
# Episode Execution
# ============================================================================

async def run_episode(
    client: Any,
    task_name: str,
    seed: int,
    episode_num: int,
) -> tuple[bool, int, float, List[float]]:
    """Run a single episode.
    
    Args:
        client: OpenAI client
        task_name: "classify", "route", or "resolve"
        seed: Random seed for reproducibility (0-29)
        episode_num: Episode counter for logging
    
    Returns:
        Tuple of (success, steps_taken, final_score, rewards_list)
    """
    env = CustomerSupportEnvironment()
    
    success = False
    steps_taken = 0
    final_score = 0.0
    rewards = []
    error_msg = None
    
    # Log episode start
    log_start(task=task_name, env=ENVIRONMENT_NAME, model=MODEL_NAME)
    
    try:
        # Reset environment
        obs = env.reset(seed=seed, task=task_name)
        
        # Single-turn: take one step
        action = get_model_action(client, task_name, obs)
        
        if action is None:
            # LLM failed - emit error step
            error_msg = "LLM response parsing failed"
            log_step(
                step=1,
                action="<failed to parse>",
                reward=0.0,
                done=True,
                error=error_msg,
            )
            steps_taken = 1
            final_score = 0.0
            rewards = [0.0]
        else:
            # Step environment
            try:
                action.validate_for_task(task_name)
                result_obs = env.step(action)
                
                reward = result_obs.reward if result_obs.reward is not None else 0.0
                done = result_obs.done if result_obs.done is not None else True
                
                # Log step
                action_str = f"category={action.category}, priority={action.priority}"
                if action.department:
                    action_str += f", department={action.department}"
                if action.requires_escalation:
                    action_str += f", escalation={action.requires_escalation}"
                if action.response:
                    action_str += f", response=<{len(action.response)} chars>"
                
                log_step(step=1, action=action_str, reward=reward, done=done, error=None)
                
                steps_taken = 1
                final_score = reward
                rewards = [reward]
                success = final_score >= SUCCESS_SCORE_THRESHOLD
            
            except Exception as step_error:
                error_msg = str(step_error)
                log_step(step=1, action="<validation failed>", reward=0.0, done=True, error=error_msg)
                steps_taken = 1
                final_score = 0.0
                rewards = [0.0]
    
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Episode failed: {e}")
        final_score = 0.0
        steps_taken = 0
        rewards = []
    
    # Log episode end
    log_end(success=success, steps=steps_taken, score=final_score, rewards=rewards)
    
    return (success, steps_taken, final_score, rewards)


# ============================================================================
# Main Benchmark
# ============================================================================

async def main():
    """Run full benchmark across all tasks and seeds.
    
    Produces:
    - [START] line per episode
    - [STEP] lines tracking action and reward
    - [END] line with final score and success flag
    """
    import time
    
    start_time = time.time()
    
    # Get LLM client
    client = get_openai_client()
    
    # Benchmark configuration: (task, difficulty)
    tasks = [
        ("classify", "easy"),
        ("route", "medium"),
        ("resolve", "hard"),
    ]
    
    results_by_task = {}
    
    # For each task, run multiple seeds
    for task_name, difficulty in tasks:
        print("\n", flush=True)  # Blank line for readability
        
        task_scores = []
        task_successes = []
        
        for seed in range(NUM_SEEDS):
            success, steps, score, rewards = await run_episode(
                client=client,
                task_name=task_name,
                seed=seed,
                episode_num=len(task_scores) + 1,
            )
            
            task_scores.append(score)
            task_successes.append(success)
        
        results_by_task[task_name] = {
            "difficulty": difficulty,
            "scores": task_scores,
            "mean_score": sum(task_scores) / len(task_scores) if task_scores else 0.0,
            "success_count": sum(1 for s in task_successes if s),
            "success_rate": sum(1 for s in task_successes if s) / len(task_successes) if task_successes else 0.0,
        }
    
    # Print summary (to stderr so it doesn't interfere with stdout evaluation)
    elapsed = time.time() - start_time
    print("\n", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print("BENCHMARK COMPLETE", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    
    for task_name, stats in results_by_task.items():
        print(
            f"{task_name.upper():12} ({stats['difficulty']:6}): "
            f"mean={stats['mean_score']:.3f}, "
            f"success_rate={stats['success_rate']:.1%}",
            file=sys.stderr,
        )
    
    print(f"Elapsed: {elapsed:.1f}s", file=sys.stderr)
    print("=" * 80, file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
