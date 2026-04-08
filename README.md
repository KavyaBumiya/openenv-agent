---
title: Customer Support RL Environment
emoji: 🎫
colorFrom: blue
colorTo: indigo
sdk: docker
sdk_version: "4.44.1"
app_file: server/app.py
app_port: 7860
pinned: false
license: mit
tags:
  - reinforcement-learning
  - openenv
  - customer-support
  - llm-agent
---

# Customer Support RL Environment

An [OpenEnv](https://github.com/openenv)-compliant RL environment
for training and evaluating LLM agents on **real-world customer-support ticket triage**.

Agents learn to classify tickets, route them to the right department, and draft
professional customer responses — tasks that mirror actual enterprise support workflows.

This environment is designed for real operational workflows in SaaS support teams:
ticket triage quality, escalation judgment, and response quality under SLA pressure.

---

## Environment Overview

| Property | Value |
|----------|-------|
| Episode type | Multi-turn (1-3 steps depending on task) |
| Dataset | 30 curated tickets across 5 categories |
| Tasks | 3 (classify → route → resolve) |
| Reward range | (0, 1) |
| Reproducible? | Yes — seeded (`seed % 30 = ticket index`) |

---

## Tasks

### 1. Classify (Easy)
Assign **category** and **priority** to a ticket.

```json
{"category": "billing", "priority": "high"}
```

Grader weights: `category=0.6, priority=0.4`

### 2. Route (Medium)
Classify the ticket and route it to the correct **department**, with an optional **escalation flag**.

```json
{
  "category": "billing",
  "priority": "high",
  "department": "billing",
  "requires_escalation": false
}
```

Grader weights: `category=0.35, priority=0.25, department=0.25, escalation=0.15`

### 3. Resolve (Hard)
Classify, route, and draft a **professional customer response**.

```json
{
  "category": "billing",
  "priority": "high",
  "department": "billing",
  "requires_escalation": false,
  "response": "Thank you for reaching out. We've identified the duplicate charge and will process your refund within 3 business days."
}
```

Grader weights: `category=0.2, priority=0.15, department=0.2, escalation=0.15, response=0.3`

---

## Reward Design

- **Priority**: graduated — 1.0 exact, 0.6 one step off, 0.2 two steps off  
- **Department**: partial credit (0.4) for tier1→tier2 or tier2↔engineering  
- **Enterprise penalty**: priority errors cost more for enterprise customers  
- **SLA penalty**: tickets open >24 h are scored more strictly on routing  
- **Response quality**: keyword coverage + empathy bonus for frustrated customers  
- **Trajectory progress**: reward is based on improvement over the best prior score  
- **Loop penalty**: repeated actions are penalized to discourage infinite loops  
- **Extra-step penalty**: each additional step costs reward, encouraging efficient completion

---

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | str | Unique ticket identifier |
| `subject` | str | Ticket subject line |
| `body` | str | Full customer message |
| `sender_tier` | str | `free` / `premium` / `enterprise` |
| `open_since_hours` | int | Hours the ticket has been open |
| `sentiment` | str | Customer emotional state |
| `previous_tickets` | int | Customer's support history count |
| `task_name` | str | Current task (`classify` / `route` / `resolve`) |
| `task_description` | str | Plain-English task instruction |
| `action_schema` | str | JSON schema of expected output |
| `policy_excerpt` | str | Relevant routing/refund policy |
| `feedback` | str | Grader explanation (empty on reset) |
| `reward` | float \| null | Score from last action (null on reset) |
| `done` | bool | Episode complete flag |

---

## Setup

### Local (Python)

```bash
git clone https://github.com/KavyaBumiya/openenv-agent.git
cd openenv-agent
pip install -r requirements.txt

# Start the environment server
uvicorn customer_support_env.server.app:app --port 7860

# Run the baseline agent (in another terminal)
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"
export HF_TOKEN="your_openai_compatible_token_here"
python inference.py
```

### Docker

```bash
docker build -t customer-support-env .
docker run \
  -e API_BASE_URL="https://router.huggingface.co/v1" \
  -e MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct" \
  -e HF_TOKEN="your_openai_compatible_token_here" \
  -p 7860:7860 \
  customer-support-env
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `https://router.huggingface.co/v1` | OpenAI-compatible LLM endpoint |
| `MODEL_NAME` | `meta-llama/Llama-3.1-8B-Instruct` | Model identifier |
| `HF_TOKEN` | required | OpenAI-compatible API token used by `inference.py` |
| `ENV_BASE_URL` | `http://localhost:7860` | Deployed environment URL used by `inference.py` |
| `LOCAL_IMAGE_NAME` | *(optional)* | Local image name for docker-image workflows |
| `BASELINE_OUTPUT_PATH` | `baseline_scores.json` | File where baseline aggregate scores are written |

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/tasks` | GET | List all 3 tasks with schemas |
| `/grader` | GET | Reward-function documentation |
| `/reset` | POST | Start episode → returns `{session_id, observation}` |
| `/step` | POST | Submit action → returns `{observation, reward, done, info}` |
| `/state` | GET | Current episode state |
| `/ws` | WS | WebSocket for real-time loops |

**Reset request:**
```json
{"task": "classify", "seed": 0}
```

**Step request:**
```json
{
  "session_id": "abc-123",
  "category": "billing",
  "priority": "high",
  "department": "billing",
  "requires_escalation": false,
  "response": "optional — only for resolve task"
}
```

---

## Baseline Scores

Measured with `meta-llama/Llama-3.1-8B-Instruct` via HuggingFace router, `temperature=0.0`, 3 seeds per task:

| Task | Difficulty | Expected Score |
|------|-----------|----------------|
| classify | Easy | 0.65 – 0.80 |
| route | Medium | 0.45 – 0.65 |
| resolve | Hard | 0.35 – 0.55 |

Scores vary with model size — larger models score consistently higher.

---

## Running the Baseline

```bash
# Copy and fill in your credentials
cp .env.example .env

# Run 9 episodes (3 tasks × 3 seeds)
python inference.py
```

The baseline script emits strict structured stdout lines required by evaluators:
```
[START] task=classify env=customer_support_env model=meta-llama/Llama-3.1-8B-Instruct
[STEP] step=1 action={"category":"billing","priority":"high","department":null,"requires_escalation":false,"response":null} reward=1.0000 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.0000

[START] task=route env=customer_support_env model=meta-llama/Llama-3.1-8B-Instruct
[STEP] step=1 action={...} reward=0.5600 done=false error=null
[STEP] step=2 action={...} reward=0.6800 done=true error=null
[END] success=true steps=2 score=0.623 rewards=0.5600,0.6800
```

No additional line types are printed to stdout.
Aggregate metrics are written to stderr and saved to `baseline_scores.json`.

## Hugging Face Space Deployment

1. Create a new Docker Space.
2. Push this repository.
3. Ensure Space secrets include `API_BASE_URL`, `MODEL_NAME`, and `HF_TOKEN`.
4. Confirm the app responds on port `7860`.

Space metadata is already included in this README frontmatter and tagged with `openenv`.

## Pre-submission Validation

Use the validator script before submitting:

```bash
chmod +x scripts/validate-submission.sh
./scripts/validate-submission.sh https://your-space.hf.space .
```

This checks:
- Space `/reset` responds with HTTP 200
- Docker build succeeds
- `openenv validate` passes

---

## Project Structure

```
customer_support_env/
├── __init__.py
├── data.py                 # 30 curated real customer tickets
├── models.py               # Typed Pydantic models (Action, Observation, State, Reward)
├── environment.py          # Core environment logic + business-aware graders
├── openenv_compat.py       # OpenEnv base class stubs
├── baseline.py             # Baseline evaluation runner
└── server/
    ├── __init__.py
    ├── app.py              # FastAPI server (REST + WebSocket)
    └── client.py           # HTTP client for environment interaction

inference.py                # Baseline agent inference script (OpenAI-compatible client)
openenv.yaml                # Full OpenEnv specification metadata
Dockerfile                  # Multi-stage container definition
requirements.txt            # All Python dependencies
main.py                      # Entry point for manual testing
tests/
├── conftest.py
├── test_environment_mock.py
└── test_integration.py
```

---

## Real-World Motivation

This environment addresses a critical gap in LLM agent training: **customer support ticket triage is a task millions of support teams actually perform daily.** Unlike toy environments:

- **Agents must make multi-step decisions** with business impact (escalation, SLA response times, refund authorization)
- **Reward signals are nuanced**, not binary — partial progress (correct category, wrong priority) yields intermediate rewards
- **Enterprise context matters** — premium/enterprise customers receive SLA pressure penalties  
- **Response quality is graded programmatically** — agents must draft coherent, policy-aware replies  
- **Dataset is curated from real patterns** — ticket categories, severity distributions, and sentiment reflect actual support workflows

Agents trained on this environment learn to:
1. Recognize category signals in customer messages  
2. Calibrate priority urgency based on enterprise tier and time-open
3. Route intelligently to appropriate specialist tiers  
4. Draft professional, contextually aware customer responses

---

## Scoring Criteria

### Evaluate Against Real Baselines

The environment provides **3 tasks with increasing difficulty**:

- **Easy (classify)**: Single decision, binary per field → models typically score **0.65–0.80**
- **Medium (route)**: Multi-field with department logic → models typically score **0.45–0.65**
- **Hard (resolve)**: Full trajectory including response generation → models typically score **0.35–0.55**

Scores decrease with model size is primary factor. Trajectory shaping ensures progress is rewarded:
- First-step correctness yields full reward
- Repeated actions are penalized (0.15) to discourage loops
- Extra steps cost 0.05 per step beyond maximum

### Grader Transparency

All scoring is deterministic and reproducible:
- **Category**: Binary (correct or incorrect)
- **Priority**: Graduated (exact=1.0, ±1 step=0.6, ±2 steps=0.2, ±3=0.0)
- **Department**: Partial credit (exact=1.0, tier1↔tier2=0.4, tier2↔engineering=0.4, else=0.0)
- **Escalation**: Binary (correct or incorrect)
- **Response**: Keyword coverage (minimum 50%, bonus for empathy to frustrated customers)
- **Enterprise/SLA penalties**: Applied when enterprise customers or SLA-critical tickets receive priority errors

---

## Running Tests

```bash
# Unit tests (environment logic)
pytest tests/test_environment_mock.py -v

# Integration tests (server + client)
pytest tests/test_integration.py -v

# Dry run (single episode, no API calls)
python main.py test
```

---

## Deployment Checklist

**Before submitting:**

1. **Environment responds:**
   ```bash
   curl -X POST http://localhost:7860/reset -H "Content-Type: application/json" -d '{"task": "classify", "seed": 0}'
   ```
   Should return HTTP 200 with a valid observation.

2. **Dockerfile builds:**
   ```bash
   docker build -t customer-support-env .
   docker run -p 7860:7860 -e HF_TOKEN="your-token" customer-support-env
   ```

3. **Baseline runs:**
   ```bash
   export API_BASE_URL="https://router.huggingface.co/v1"
   export MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"
   export HF_TOKEN="your-api-key"
   python inference.py
   ```
   Produces `baseline_scores.json` with results.

4. **openenv validate passes:**
   ```bash
   pip install openenv-core
   openenv validate
   ```

---

## Citation

If you use this environment in published research, please cite:

```bibtex
@misc{customer_support_env,
  title={Customer Support RL Environment: OpenEnv benchmark for LLM agent triage},
  author={Kavya B.},
  year={2026}
}
```

---

## License

MIT — See [LICENSE](LICENSE) for details.
