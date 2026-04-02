#!/usr/bin/env python3
"""
inference.py — OpenEnv baseline agent for customer_support_env
===============================================================

Calls the deployed environment via HTTP and queries the LLM using the
OpenAI-compatible client (works with HuggingFace router, Groq, Ollama, etc.).

Required environment variables:
    API_BASE_URL   LLM endpoint  (default: https://router.huggingface.co/v1)
    MODEL_NAME     Model name    (default: meta-llama/Llama-3.1-8B-Instruct)
    HF_TOKEN       API token (required)

Optional:
    ENV_BASE_URL   Deployed environment URL
                                 (default: http://localhost:7860 — for local docker testing)
    BASELINE_OUTPUT_PATH   JSON path for deterministic score summary
                                                 (default: baseline_scores.json)

Usage:
    export HF_TOKEN="hf_..."   # or OPENAI_API_KEY
  python inference.py
"""

import json
import os
import re
import textwrap
from typing import List, Optional

import httpx
from openai import OpenAI

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "meta-llama/Llama-3.1-8B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN", "")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME", "")
BASELINE_OUTPUT_PATH = os.getenv("BASELINE_OUTPUT_PATH", "baseline_scores.json")

BENCHMARK       = "customer_support_env"
TASKS           = ["classify", "route", "resolve"]
NUM_SEEDS       = 3        # seeds per task  →  9 total episodes
SEEDS           = list(range(NUM_SEEDS))
MAX_STEPS       = 5
TEMPERATURE     = 0.0
MAX_TOKENS      = 512
SUCCESS_THRESH  = 0.1      # episode counted as success if score >= this

# ---------------------------------------------------------------------------
# Validate credentials early
# ---------------------------------------------------------------------------
if not HF_TOKEN:
    raise RuntimeError("Missing API key. Set HF_TOKEN.")

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


def log_end(success: bool, steps: int, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}", flush=True)

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


def call_llm(task: str, obs: dict, episode_seed: int, step: int) -> Optional[dict]:
    """Query the LLM and return a parsed action dict, or None on failure."""
    try:
        resp = llm_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPTS[task]},
                {"role": "user",   "content": build_user_prompt(obs)},
            ],
            temperature=TEMPERATURE,
            top_p=1.0,
            seed=(episode_seed * 100) + step,
            max_tokens=MAX_TOKENS,
        )
        raw = (resp.choices[0].message.content or "").strip()
        return extract_json(raw, REQUIRED_KEYS[task])
    except Exception as exc:
        _ = exc
        return None

# ---------------------------------------------------------------------------
# Episode runner
# ---------------------------------------------------------------------------

def run_episode(task: str, seed: int) -> tuple[bool, float]:
    env = EnvClient(ENV_BASE_URL)
    rewards: List[float] = []
    steps = 0
    success = False
    final_obs: dict = {}

    log_start(task=task, env=BENCHMARK, model=MODEL_NAME)

    try:
        obs = env.reset(task=task, seed=seed)

        for step in range(1, MAX_STEPS + 1):
            action_dict = call_llm(task, obs, episode_seed=seed, step=step)
            error_msg = None

            if action_dict is None:
                error_msg = "LLM parse failed - using fallback"
                action_dict = {
                    "category": "general",
                    "priority": "low",
                    "department": "tier1",
                    "requires_escalation": False,
                    "response": "Thanks for reaching out. We are reviewing this now and will follow up with next steps shortly.",
                }

            payload: dict = {
                "category": action_dict.get("category", "general"),
                "priority": action_dict.get("priority", "low"),
                "department": action_dict.get("department"),
                "requires_escalation": action_dict.get("requires_escalation", False),
                "response": action_dict.get("response"),
            }

            result = env.step(payload)
            reward = float(result.get("reward", 0.0))
            done = bool(result.get("done", True))
            final_obs = result.get("observation", {}) or {}
            last_action_error = final_obs.get("last_action_error") if isinstance(final_obs, dict) else None

            rewards.append(reward)
            steps = step

            action_str = (
                f"category={payload['category']} priority={payload['priority']}"
                + (f" dept={payload['department']}" if payload.get("department") else "")
                + (f" esc={str(payload['requires_escalation']).lower()}" if payload.get("requires_escalation") is not None else "")
                + (f" resp=<{len(payload['response'])}chars>" if payload.get("response") else "")
            )
            log_step(
                step=step,
                action=action_str,
                reward=reward,
                done=done,
                error=last_action_error if last_action_error is not None else error_msg,
            )

            obs = final_obs
            if done:
                break

        score = sum(rewards)
        success = score >= SUCCESS_THRESH and bool(final_obs)

    except Exception:
        # Keep stdout strict: no extra line types besides START/STEP/END.
        success = False
    finally:
        env.close()
        final_rewards = rewards or [0.0]
        final_steps = steps or 0
        log_end(success=success, steps=final_steps, rewards=final_rewards)

    return success, sum(rewards or [0.0])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    results: dict[str, list[float]] = {task: [] for task in TASKS}
    for task in TASKS:
        for seed in SEEDS:
            _, total_reward = run_episode(task, seed)
            results[task].append(total_reward)

    summary = {
        "benchmark": BENCHMARK,
        "model_name": MODEL_NAME,
        "api_base_url": API_BASE_URL,
        "episodes_per_task": len(SEEDS),
        "task_scores": {},
    }

    # Keep strict stdout reserved for [START]/[STEP]/[END] lines only.
    # Baseline aggregates are written to stderr for operator visibility.
    for task in TASKS:
        task_scores = results[task]
        mean_score = (sum(task_scores) / len(task_scores)) if task_scores else 0.0
        summary["task_scores"][task] = {
            "mean_total_reward": round(mean_score, 4),
            "episode_rewards": [round(v, 4) for v in task_scores],
        }
        print(
            f"task={task} episodes={len(task_scores)} mean_total_reward={mean_score:.3f} "
            f"model={MODEL_NAME} api_base={API_BASE_URL} local_image={LOCAL_IMAGE_NAME or 'none'}",
            file=os.sys.stderr,
            flush=True,
        )

    overall_scores = [score for task_scores in results.values() for score in task_scores]
    summary["overall_mean_total_reward"] = round(
        (sum(overall_scores) / len(overall_scores)) if overall_scores else 0.0,
        4,
    )

    with open(BASELINE_OUTPUT_PATH, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)

    print(f"wrote_baseline_summary={BASELINE_OUTPUT_PATH}", file=os.sys.stderr, flush=True)


if __name__ == "__main__":
    main()
