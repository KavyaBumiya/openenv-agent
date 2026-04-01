#!/usr/bin/env python3
"""
inference.py — OpenEnv baseline agent for customer_support_env
===============================================================

Calls the deployed environment via HTTP and queries the LLM using the
OpenAI-compatible client (works with HuggingFace router, Groq, Ollama, etc.).

Required environment variables:
  API_BASE_URL   LLM endpoint  (default: https://router.huggingface.co/v1)
  MODEL_NAME     Model name    (default: meta-llama/Llama-3.1-8B-Instruct)
  HF_TOKEN       API token     (required)

Optional:
  ENV_BASE_URL   Deployed environment URL
                 (default: http://localhost:7860 — for local docker testing)

Usage:
  export HF_TOKEN="hf_..."
  python inference.py
"""

import asyncio
import json
import logging
import os
import re
import sys
import textwrap
from typing import List, Optional

import httpx
from openai import OpenAI

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "meta-llama/Llama-3.1-8B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")

BENCHMARK       = "customer_support_env"
TASKS           = ["classify", "route", "resolve"]
NUM_SEEDS       = 3        # seeds per task  →  9 total episodes
TEMPERATURE     = 0.3
MAX_TOKENS      = 512
SUCCESS_THRESH  = 0.1      # episode counted as success if score >= this

# ---------------------------------------------------------------------------
# Validate credentials early
# ---------------------------------------------------------------------------
if not HF_TOKEN:
    print("[ERROR] HF_TOKEN is not set. Export it and retry.", flush=True)
    sys.exit(1)

# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------
llm_client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)

# ---------------------------------------------------------------------------
# Structured logging helpers  (spec-required format)
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float,
             done: bool, error: Optional[str]) -> None:
    err = error if error else "null"
    print(
        f"[STEP] step={step} action={action[:120]} "
        f"reward={reward:.2f} done={str(done).lower()} error={err}",
        flush=True,
    )


def log_end(success: bool, steps: int,
            score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )

# ---------------------------------------------------------------------------
# Environment HTTP client
# ---------------------------------------------------------------------------

class EnvClient:
    """Thin wrapper around the FastAPI environment server."""

    def __init__(self, base_url: str, timeout: float = 60.0):
        self.base = base_url.rstrip("/")
        self.http  = httpx.Client(timeout=timeout)
        self.session_id: Optional[str] = None

    def reset(self, task: str, seed: int) -> dict:
        r = self.http.post(
            f"{self.base}/reset",
            json={"task": task, "seed": seed},
        )
        r.raise_for_status()
        data = r.json()
        self.session_id = data["session_id"]
        return data["observation"]

    def step(self, action: dict) -> dict:
        payload = {"session_id": self.session_id, **action}
        r = self.http.post(f"{self.base}/step", json=payload)
        r.raise_for_status()
        return r.json()   # {observation, reward, done}

    def close(self) -> None:
        self.http.close()

# ---------------------------------------------------------------------------
# LLM prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS = {
    "classify": textwrap.dedent("""\
        You are a customer-support triage specialist.
        Read the ticket and respond with ONLY a JSON object — no markdown, no explanation.
        Format:
        {"category": "billing|technical|account|shipping|general",
         "priority": "low|medium|high|urgent"}"""),

    "route": textwrap.dedent("""\
        You are a customer-support routing specialist.
        Read the ticket and respond with ONLY a JSON object — no markdown, no explanation.
        Format:
        {"category": "billing|technical|account|shipping|general",
         "priority": "low|medium|high|urgent",
         "department": "tier1|tier2|billing|engineering|management",
         "requires_escalation": true|false}"""),

    "resolve": textwrap.dedent("""\
        You are a customer-support representative.
        Read the ticket and respond with ONLY a JSON object — no markdown, no explanation.
        The "response" field must be a professional reply to the customer.
        Format:
        {"category": "billing|technical|account|shipping|general",
         "priority": "low|medium|high|urgent",
         "department": "tier1|tier2|billing|engineering|management",
         "requires_escalation": true|false,
         "response": "<your reply to the customer>"}"""),
}

REQUIRED_KEYS = {
    "classify": ["category", "priority"],
    "route":    ["category", "priority", "department", "requires_escalation"],
    "resolve":  ["category", "priority", "department", "requires_escalation", "response"],
}


def build_user_prompt(obs: dict) -> str:
    return textwrap.dedent(f"""\
        Ticket ID: {obs.get('ticket_id')}
        Tier: {obs.get('sender_tier')}
        Sentiment: {obs.get('sentiment')}
        Open for: {obs.get('open_since_hours')} hours

        Subject: {obs.get('subject')}

        Body:
        {obs.get('body')}

        Task: {obs.get('task_description')}

        Policy:
        {obs.get('policy_excerpt', '')}
        """).strip()


def extract_json(text: str, required_keys: List[str]) -> Optional[dict]:
    """Try multiple strategies to get a valid JSON dict from the LLM response."""
    candidates = []

    # 1. Direct parse
    try:
        candidates.append(json.loads(text.strip()))
    except json.JSONDecodeError:
        pass

    # 2. Markdown fence
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        try:
            candidates.append(json.loads(m.group(1)))
        except json.JSONDecodeError:
            pass

    # 3. First {...} block
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            candidates.append(json.loads(m.group(0)))
        except json.JSONDecodeError:
            pass

    for d in candidates:
        if isinstance(d, dict) and all(k in d for k in required_keys):
            return d
    return None


def call_llm(task: str, obs: dict) -> Optional[dict]:
    """Query the LLM and return a parsed action dict, or None on failure."""
    try:
        resp = llm_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPTS[task]},
                {"role": "user",   "content": build_user_prompt(obs)},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        raw = (resp.choices[0].message.content or "").strip()
        return extract_json(raw, REQUIRED_KEYS[task])
    except Exception as exc:
        logging.warning("LLM call failed: %s", exc)
        return None

# ---------------------------------------------------------------------------
# Episode runner
# ---------------------------------------------------------------------------

def run_episode(env: EnvClient, task: str, seed: int) -> None:
    rewards: List[float] = []
    steps = 0
    score = 0.0
    success = False

    log_start(task=task, env=BENCHMARK, model=MODEL_NAME)

    try:
        obs = env.reset(task=task, seed=seed)

        action_dict = call_llm(task, obs)
        error_msg = None

        if action_dict is None:
            error_msg = "LLM parse failed — using fallback"
            # Minimal valid action so environment doesn't crash
            action_dict = {
                "category": "general",
                "priority": "low",
                "department": "tier1",
                "requires_escalation": False,
                "response": "Thank you for contacting us. We will follow up shortly.",
            }

        # Build step payload (only include keys valid for this task)
        payload: dict = {
            "category":           action_dict.get("category", "general"),
            "priority":           action_dict.get("priority", "low"),
            "department":         action_dict.get("department"),
            "requires_escalation": action_dict.get("requires_escalation", False),
            "response":           action_dict.get("response"),
        }

        result   = env.step(payload)
        reward   = float(result.get("reward", 0.0))
        done     = bool(result.get("done", True))

        rewards.append(reward)
        steps = 1

        # Human-readable action string for the log
        action_str = (
            f"category={payload['category']} priority={payload['priority']}"
            + (f" dept={payload['department']}" if payload.get("department") else "")
            + (f" esc={payload['requires_escalation']}" if payload.get("requires_escalation") else "")
            + (f" resp=<{len(payload['response'])}chars>" if payload.get("response") else "")
        )

        log_step(step=1, action=action_str, reward=reward, done=done, error=error_msg)

        score   = reward
        success = score >= SUCCESS_THRESH

    except Exception as exc:
        log_step(step=steps + 1, action="<error>", reward=0.0, done=True, error=str(exc))
        rewards = rewards or [0.0]
        score   = 0.0

    log_end(success=success, steps=steps or 1, score=score, rewards=rewards or [0.0])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    env = EnvClient(ENV_BASE_URL)
    try:
        for task in TASKS:
            print(flush=True)   # blank line between tasks for readability
            for seed in range(NUM_SEEDS):
                run_episode(env, task, seed)
    finally:
        env.close()


if __name__ == "__main__":
    main()
