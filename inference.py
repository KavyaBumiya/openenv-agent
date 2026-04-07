#!/usr/bin/env python3
"""
inference.py — OpenEnv baseline agent for customer_support_env
===============================================================

Calls the deployed environment via HTTP and queries the LLM using the
OpenAI-compatible client.

Required environment variables:
    API_BASE_URL      LLM endpoint  (default: https://router.huggingface.co/v1)
    MODEL_NAME        Model name    (default: meta-llama/Llama-3.1-8B-Instruct)
    HF_TOKEN          API token (or OPENAI_API_KEY for OpenAI direct)

Optional:
    OPENAI_API_KEY    OpenAI API key (validators will inject this)
    ENV_BASE_URL      Deployed environment URL (default: http://localhost:7860)
    BASELINE_OUTPUT_PATH   JSON path for baseline scores (default: baseline_scores.json)
    LOCAL_IMAGE_NAME      Preserved for submission harness compatibility

Usage:
    export HF_TOKEN="..."
    export OPENAI_API_KEY="sk-..."  # optional for local testing
    python inference.py

Note:
    During validator testing, OPENAI_API_KEY will be injected automatically.
    This script gracefully handles missing API keys with fallback behavior.
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
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")
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
SUCCESS_THRESH  = 0.5      # episode counted as success if normalized score >= this
STRICT_SCORE_EPSILON = 0.001

# ---------------------------------------------------------------------------
# Validate credentials early
# ---------------------------------------------------------------------------
if not HF_TOKEN:
    raise RuntimeError("Missing API token. Set HF_TOKEN.")

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
    err = _sanitize_single_line(error) if error else "null"
    print(
        f"[STEP] step={step} action={_sanitize_single_line(action)} "
        f"reward={reward:.4f} done={str(done).lower()} error={err}",
        flush=True,
    )


def log_end(success: bool, steps: int, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.4f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}", flush=True)


def _sanitize_single_line(value: Optional[str]) -> str:
    if value is None:
        return "null"
    return value.replace("\r", " ").replace("\n", " ").strip()


def _validate_strict_score(score: float, label: str = "score") -> float:
    """Validate and clamp a score to be strictly in (0, 1).
    
    DEFENSIVE: This function ensures NO score ever escapes unclamped.
    Phase 2 validator requires: 0 < score < 1 (strictly)
    """
    # Handle invalid types
    if not isinstance(score, (int, float)):
        print(f"[WARN] Score {label} has invalid type {type(score).__name__}, using epsilon", file=os.sys.stderr, flush=True)
        return STRICT_SCORE_EPSILON
    
    # Handle NaN
    if score != score:
        print(f"[WARN] Score {label} is NaN, using epsilon", file=os.sys.stderr, flush=True)
        return STRICT_SCORE_EPSILON
    
    # Handle infinity
    if score == float('inf') or score == float('-inf'):
        print(f"[WARN] Score {label} is infinite, using midpoint", file=os.sys.stderr, flush=True)
        return 0.5
    
    # Clamp to strict bounds
    clamped = round(min(1.0 - STRICT_SCORE_EPSILON, max(STRICT_SCORE_EPSILON, score)), 4)
    
    # Log if clamping happened
    if score == 0.0:
        print(f"[WARN] Score {label}=0.0 clamped to {clamped}", file=os.sys.stderr, flush=True)
    elif score == 1.0:
        print(f"[WARN] Score {label}=1.0 clamped to {clamped}", file=os.sys.stderr, flush=True)
    elif abs(score - clamped) > 0.0005:
        print(f"[WARN] Score {label}={score:.4f} clamped to {clamped:.4f}", file=os.sys.stderr, flush=True)
    
    # Final check: ensure strictly in (0, 1)
    if clamped <= 0.0 or clamped >= 1.0:
        print(f"[ERROR] Score {label}={clamped} is NOT strictly in (0, 1)! Using 0.5", file=os.sys.stderr, flush=True)
        return 0.5
    
    return clamped



def _episode_score(rewards: List[float]) -> float:
    """Return a normalized per-episode score in [0, 1]."""
    if not rewards:
        return STRICT_SCORE_EPSILON
    return round(min(1.0 - STRICT_SCORE_EPSILON, max(STRICT_SCORE_EPSILON, sum(rewards))), 4)


def _strict_summary_score(value: float) -> float:
    return round(min(1.0 - STRICT_SCORE_EPSILON, max(STRICT_SCORE_EPSILON, value)), 4)


def _strict_task_score(value: float) -> float:
    """Return a task-level score guaranteed to be strictly inside (0, 1)."""
    return _strict_summary_score(value)

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
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = None
            try:
                payload_data = r.json()
                if isinstance(payload_data, dict):
                    detail = payload_data.get("detail") or payload_data.get("message")
            except Exception:
                detail = None
            message = detail or r.text or str(exc)
            raise RuntimeError(message) from exc
        return r.json()   # {observation, reward, done}

    def close(self) -> None:
        self.http.close()

    def wait_until_ready(self, attempts: int = 10, delay_s: float = 1.5) -> None:
        for _ in range(attempts):
            try:
                r = self.http.get(f"{self.base}/health")
                r.raise_for_status()
                return
            except Exception:
                import time

                time.sleep(delay_s)
        raise RuntimeError(f"Environment server not reachable at {self.base}")

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


def call_llm(task: str, obs: dict, episode_seed: int, step: int) -> tuple[Optional[dict], Optional[str]]:
    """Query the LLM and return (action_dict, error_message)."""
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
        parsed = extract_json(raw, REQUIRED_KEYS[task])
        if parsed is None:
            return None, "LLM parse failed - using fallback"
        return parsed, None
    except Exception as exc:
        return None, _sanitize_single_line(str(exc))

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
            action_dict, llm_error = call_llm(task, obs, episode_seed=seed, step=step)
            error_msg = llm_error

            if action_dict is None:
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

            result = None
            reward = STRICT_SCORE_EPSILON
            done = False
            final_obs: dict = {}
            step_error: Optional[str] = error_msg

            try:
                result = env.step(payload)
                reward = _strict_summary_score(float(result.get("reward", 0.0)))
                done = bool(result.get("done", True))
                final_obs = result.get("observation", {}) or {}
                last_action_error = final_obs.get("last_action_error") if isinstance(final_obs, dict) else None
                if last_action_error is not None:
                    step_error = str(last_action_error)
            except Exception as exc:
                reward = STRICT_SCORE_EPSILON
                done = True
                final_obs = obs or {}
                step_error = str(exc)

            rewards.append(reward)
            steps = step

            action_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            log_step(
                step=step,
                action=action_str,
                reward=reward,
                done=done,
                error=step_error,
            )

            obs = final_obs
            if done:
                break

        score = _episode_score(rewards)
        success = steps > 0 and score >= SUCCESS_THRESH

    except Exception:
        # Keep stdout strict: no extra line types besides START/STEP/END.
        success = False
    finally:
        try:
            env.close()
        except Exception as exc:
            print(f"[WARN] env.close failed: {_sanitize_single_line(str(exc))}", file=os.sys.stderr, flush=True)
        final_rewards = rewards or [0.0]
        final_steps = steps or 0
        log_end(
            success=success,
            steps=final_steps,
            rewards=final_rewards,
        )

    return success, _episode_score(rewards)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Probe /health once up front rather than for every episode.
    probe_env = EnvClient(ENV_BASE_URL)
    try:
        probe_env.wait_until_ready()
    finally:
        probe_env.close()

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
        "task_score_details": {},
    }

    # Keep strict stdout reserved for [START]/[STEP]/[END] lines only.
    # Baseline aggregates are written to stderr for operator visibility.
    for task in TASKS:
        task_scores = results[task]
        mean_score = (sum(task_scores) / len(task_scores)) if task_scores else 0.0
        
        # DEFENSIVE: Comprehensively validate task scores
        strict_mean = _validate_strict_score(mean_score, f"task_mean_score[{task}]")
        summary["task_scores"][task] = strict_mean
        
        # Also validate each episode reward
        validated_episode_rewards = [_validate_strict_score(v, f"episode_reward[{task}]") for v in task_scores]
        
        summary["task_score_details"][task] = {
            "mean_episode_score": strict_mean,
            "episode_rewards": validated_episode_rewards,
        }
        print(
            f"task={task} episodes={len(task_scores)} mean_episode_score={mean_score:.3f} "
            f"model={MODEL_NAME} api_base={API_BASE_URL} local_image={LOCAL_IMAGE_NAME or 'none'}",
            file=os.sys.stderr,
            flush=True,
        )

    overall_scores = [score for task_scores in results.values() for score in task_scores]
    overall_mean = (sum(overall_scores) / len(overall_scores)) if overall_scores else 0.0
    validated_overall_mean = _validate_strict_score(overall_mean, "overall_mean_episode_score")
    summary["overall_mean_episode_score"] = validated_overall_mean
    
    # FINAL VALIDATION BEFORE JSON OUTPUT
    print("\n" + "="*60, file=os.sys.stderr, flush=True)
    print("FINAL VALIDATION CHECK", file=os.sys.stderr, flush=True)
    print("="*60, file=os.sys.stderr, flush=True)
    
    all_scores_to_check = list(summary["task_scores"].values()) + [summary["overall_mean_episode_score"]]
    all_scores_to_check.extend(s for task_detail in summary["task_score_details"].values() for s in task_detail["episode_rewards"])
    
    for i, score in enumerate(all_scores_to_check):
        if not (0 < score < 1):
            print(f"❌ VALIDATION FAILED: Score #{i} = {score} is NOT strictly in (0, 1)", file=os.sys.stderr, flush=True)
        else:
            print(f"✅ Score #{i} = {score:.4f} is valid", file=os.sys.stderr, flush=True)
    
    print("="*60 + "\n", file=os.sys.stderr, flush=True)

    with open(BASELINE_OUTPUT_PATH, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)

    print(f"wrote_baseline_summary={BASELINE_OUTPUT_PATH}", file=os.sys.stderr, flush=True)


if __name__ == "__main__":
    main()
