# Customer Support Ticket Triage Environment 🎫

An **OpenEnv reinforcement learning environment** for training and evaluating autonomous agents to classify, route, and resolve customer support tickets.

**🎯 Real-world task** | **📊 Progressive difficulty** | **💰 Business-aware grading** | **✅ Benchmark-ready**

---

## ⚡ Quick Start

### 1. Installation

```bash
python -m venv .venv
.venv\Scripts\activate              # Windows
# source .venv/bin/activate         # macOS/Linux

pip install -r requirements.txt
```

### 2. Set API Key

```powershell
$env:GROQ_API_KEY="gsk_..."         # Windows PowerShell
# export GROQ_API_KEY="gsk_..."     # macOS/Linux
```

### 3. Run Environment (Single Entry Point)

```bash
# Show menu
python main.py

# Quick verification (no API key needed)
python main.py test

# Official benchmark (judge-ready, reproducible)
python run_official_benchmark.py

# Full baseline with Groq (training mode, variable temperature)
python main.py baseline --mode training

# Start API server
python main.py server

# Interactive demo
python main.py demo
```

**See [MAIN_USAGE.md](MAIN_USAGE.md) for complete guide**

### 4. View API Documentation

When server is running: **http://localhost:8000/docs**

---

## 🎮 Three Tasks (Easy → Hard)

### EASY: Classify
Predict category + priority  
**Output**: `{"category": "...", "priority": "..."}`  

### MEDIUM: Route
+ Department routing + escalation flag  
**Output**: `{..., "department": "...", "requires_escalation": bool}`  

### HARD: Resolve
+ Professional response generation  
**Output**: `{..., "response": "..."}`  
***Penalty***: Missing response = -50% (ensures responses are required)

---

## 📊 Dataset

**30 real-world support tickets** with:
- ✅ Realistic language (typos, frustration, natural flow)
- ✅ Business context (enterprise penalties, SLA visibility)
- ✅ Multi-label metadata (sentiment, previous history, open duration)
- ✅ Progressive difficulty (easy categories → ambiguous routings → emotional responses)

---

## 📈 Baseline Evaluation (2 Modes)

### Official Benchmark Mode (Judge-Ready)

**For reproducible, comparable scores:**
```bash
python run_official_benchmark.py
```

Settings:
- Temperature: **0.1 all tasks** (deterministic)
- Dataset: Full sweep (30 episodes per task)
- Reproducibility: Same scores every run
- Use case: Official submissions, judges, final results

### Training Mode (Exploratory)

**For development and experimentation:**
```bash
python -m customer_support_env.baseline --mode training
```

Settings:
- Temperature: 0.1 classify, 0.5 route, 0.7 resolve (variant difficulty)
- Dataset: Full sweep (30 episodes per task)
- Use case: Prompt tuning, strategy exploration

---

**Model**: Groq Llama-3.3-70b-versatile  
**Typical Official Scores**: Classify ~70%, Route ~60%, Resolve ~50%  
(Exact scores vary with prompting strategy)

---

## 🏗️ Architecture

```
customer_support_env/
├── environment.py         # Core RL simulator
├── models.py             # Pydantic schemas (OpenEnv compliant)
├── data.py               # 30 tickets dataset
├── baseline.py           # Groq evaluation script
├── server/
│   ├── app.py            # FastAPI endpoints
│   └── client.py         # Python SDK
└── openenv_compat.py     # OpenEnv interface

tests/
├── test_environment_mock.py
└── test_groq_integration.py

evals/
├── test_difficulty_levels.py
├── test_difficulty_comprehensive.py
├── test_improved_training.py
└── ...

Dockerfile                 # Production container
```

---

## 🚀 Docker Deployment

```bash
# Build
docker build -t customer-support-env .

# Run (exposes port 8000)
docker run -p 8000:8000 \
  -e GROQ_API_KEY="gsk_..." \
  customer-support-env

# Test
curl http://localhost:8000/tasks
```

---

## 🔗 Full Documentation

See **[README_PRODUCTION.md](./README_PRODUCTION.md)** for:
- ✅ Complete OpenEnv spec compliance details
- ✅ Reward function deep-dive (enterprise penalties, SLA logic)
- ✅ API reference & examples
- ✅ HuggingFace Spaces deployment guide
- ✅ Training recommendations
- ✅ Debugging tips

---

## 💡 Example Usage

```python
from customer_support_env import CustomerSupportEnvironment
from customer_support_env.models import TicketAction

env = CustomerSupportEnvironment()

# 10 episodes of classify task
for seed in range(10):
    obs = env.reset(seed=seed, task="classify")
    
    # Your agent decides
    action = TicketAction(
        category="billing",
        priority="high",
        department=None,
        requires_escalation=False,
        response=None
    )
    
    obs = env.step(action)
    print(f"Reward: {obs.reward:.2f}")
    print(f"Feedback: {obs.feedback}")
```

---

## 📦 Dependencies

```
pydantic>=2.0
fastapi
uvicorn
groq
```

See `requirements.txt` for versions.

---

## 🎯 Why This Environment?

✅ **Real-world task**: Not games—actual support workflows  
✅ **Business metrics**: Enterprise penalties, SLA awareness, escalation logic  
✅ **OpenEnv compliant**: Full spec with typed models & deterministic episodes  
✅ **Benchmark-ready**: Dual-mode evaluation (official reproducible + training exploratory)  
✅ **Interpretable rewards**: Transparent grading with detailed feedback    

---

## 🤝 Contributing

Found a bug? Fork the repo and submit a PR!

Suggested improvements:
- [ ] Add multi-turn dialogue support
- [ ] Augmentation script for 30 → 300 tickets
- [ ] Few-shot prompt templates
- [ ] Model comparison dashboard

---

## 📜 License

MIT - Use freely in research or production

---

## ❓ Questions?

- **Full API docs**: http://localhost:8000/docs
- **Production guide**: [README_PRODUCTION.md](./README_PRODUCTION.md)
- **Dataset explorer**: See `customer_support_env/data.py`

---

**Status**: ✅ Stable research environment | **Last updated**: March 2026

### Files

- **models.py** — Defines the contract between agent, environment, and grader
  - `TicketAction` — Agent's decision (category, priority, department, response)
  - `TicketObservation` — What the agent reads
  - `TicketState` — Episode metadata

- **data.py** — 30 carefully crafted customer support tickets with ground truth labels
  - 7 billing, 8 technical, 6 account, 5 general, 4 shipping
  - Distribution: 10 free tier, 14 premium, 6 enterprise
  - Includes intentional edge cases

- **environment.py** — Core game logic
  - Single-turn environment: reset → step → done=True
  - Shaped reward signals per task
  - Reproducible with seed-based ticket selection

- **server/client.py** — WebSocket serialization (TicketAction ↔ JSON)

- **server/app.py** — FastAPI server with required endpoints
  - `/tasks` — Task definitions for evaluation
  - `/grader` — Scoring philosophy explanation
  - `/baseline` — Execute baseline.py and return results
  - Standard OpenEnv endpoints: `/ws`, `/reset`, `/step`, `/state`, `/health`

- **baseline.py** — Reference evaluation script
  - Groq Llama-3.3-70b-versatile on full dataset sweep per task (30 episodes total)
  - Reproducible with seeded episodes and task-specific temperature settings
  - JSON output with score statistics

### Tasks

All tasks require the agent to correctly classify tickets, but with increasing complexity:

1. **Classify** (Easy)
   - Agent outputs: category, priority
   - Weights: category 60%, priority 40%

2. **Route** (Medium)
   - Agent outputs: category, priority, department, escalation flag (optional)
   - Weights: category 35%, priority 25%, department 25%, escalation 15%

3. **Resolve** (Hard)
   - Agent outputs: category, priority, department, escalation flag (optional), response
   - Weights: category 20%, priority 15%, department 20%, escalation 15%, response 30%

### Reward Design

The reward function implements realistic business logic that encourages agents to act like professional support teams:

- **Category** (binary): Correct classification (1.0) or incorrect (0.0)

- **Priority** (graduated, business-aware): 
  - Exact match: 1.0
  - One level off (e.g., high vs urgent): 0.6
  - Two levels off: 0.2
  - Three+ levels off: 0.0
  - **Enterprise Penalty** (×0.7): Enterprise tier customers get stricter grading for priority errors because they expect higher service standards
  - **SLA Penalty** (×0.85): Tickets open >24 hours multiply priority error cost by 0.85, reflecting time pressure

- **Department** (graduated):
  - Exact match: 1.0
  - Fallback logic: routing to tier1 when tier2 expected = 0.4 (acknowledges that some misroutes are acceptable)
  - Wrong department: 0.0

- **Escalation** (binary): Correct judgment about when to escalate (1.0) or incorrect/missing (0.0)

- **Response** (keyword-based, sentiment-aware):
  - Requires 75% of required keywords for full credit
  - Scoring: all keywords=1.0, most=0.6, half=0.3, few=0.0
  - **Sentiment Bonus** (+0.1): If customer sentiment is frustrated/angry and response contains empathy keywords (sorry, understand, apologize, thank you, appreciate, happy to help), agent gets +0.1 bonus

This design teaches agents that:
1. Correct classification is fundamental
2. Getting close on priority is better than being wrong, especially for high-value customers
3. Routing and escalation judgment are critical decisions
4. Response tone matters — matching customer emotion with empathy earns higher scores
5. Some mistakes are more forgivable than others (which reflects real business logic)

### Dataset Design

**Ticket Schema:**
Each of the 30 tickets includes:
- **Identity**: id, subject, body, sender_tier (free/premium/enterprise)
- **Context**: previous_tickets (count), open_since_hours (1-48), sentiment (frustrated/positive/neutral/angry/urgent/confused)
- **Ground Truth**: category, priority, department, requires_escalation (bool), response_keywords (list)
- **Metadata**: _why (reasoning for labels)

These fields enable the grader to implement realistic business logic without requiring the agent to make decisions beyond the action schema.

**Categories:**
- Billing: Charges, refunds, invoices, pricing questions
- Technical: Login failures, API errors, performance issues, bugs
- Account: Password resets, account deletion, ownership transfer, security
- General: Feedback, partnerships, feature requests, documentation
- Shipping: Order tracking, damaged goods, delivery issues

**Edge Cases (intentional):**
- Ticket TKT-015: Sounds like billing (charge) but is account (cancelled?)
- Ticket TKT-020: Angry language with urgent tone — doesn't change category
- Tickets TKT-022, TKT-025: Business inquiries requiring judgment
- Enterprise tickets with high stakes (e.g., TKT-002: duplicate charge = trust issue)
- Tickets with >24h open time to test SLA urgency modeling

**Priority Decision Rules:**
- Free tier: Generally lower priority (free customers have lower SLA)
- Premium: Medium-high priority
- Enterprise: High-urgent (expectations for perfection)
- Blocking issues: Always high or urgent
- Production impact: Urgent
- Customer emotion: Frustrated/angry customers need responses even if technically "low" priority

## Design Philosophy

### Minimal Contract (models.py)

Every field serves one of two purposes:
1. Help the agent understand the task
2. Give the grader what it needs to score

Fields that do neither: remove them.

### Human-Centered Dataset (data.py)

- Real customer voices: typos, run-on sentences, frustration
- Explicit reasoning for every label
- Deliberate distribution for learning

### Deterministic Grading (environment.py)

- No randomness in scoring
- Same action + same ticket = same score, always
- No LLM calls in graders (string comparison only)

### Reproducible Evaluation (baseline.py)

- seed=episode_number guarantees same ticket each run
- Can reproduce exact scores across machines
- Verified with Groq Llama-3.3-70b-versatile
- For official benchmarks, use single low-temperature pass or report multi-run mean ± std

## Extensibility

### Adding More Tickets

Edit `customer_support_env/data.py`:
1. Follow the format in TICKETS list
2. Ensure you have ground truth labels
3. Add `_why` field explaining your reasoning
4. Update TICKETS count to ≥30

### Changing Reward Weights

Edit `environment.py`:
1. Modify `REWARD_WEIGHTS` dictionary
2. Ensure weights per task sum to 1.0
3. Test with: `python -m customer_support_env.baseline`

### Adding a 4th Task

1. Add task definition to `DIFFICULTY_MAP`, `ACTION_SCHEMAS`, `TASK_DESCRIPTIONS`
2. Add case in `_grade()` method with task weights
3. Add task to `/tasks` endpoint in `app.py`
4. Test with baseline

## Testing

```bash
# Verify dataset
python -c "from customer_support_env.data import TICKETS; print(f'Loaded {len(TICKETS)} tickets')"

# Test environment
python -c "
from customer_support_env.environment import CustomerSupportEnvironment
from customer_support_env.models import TicketAction

env = CustomerSupportEnvironment()
obs = env.reset(task='classify', seed=0)
print(f'Ticket: {obs.subject}')
action = TicketAction(category='billing', priority='high')
result = env.step(action)
print(f'Score: {result.reward}')
"
```

## API Reference

### POST /reset

Reset environment for new episode.

```json
{
  "task": "classify",
  "seed": 0,
  "episode_id": "ep-001"
}
```

### POST /step

Submit action and get reward.

```json
{
  "category": "billing",
  "priority": "high",
  "department": "billing",
  "response": "Thank you for reporting this issue..."
}
```

### GET /tasks

Get all task definitions (used by evaluator).

### GET /grader

Get scoring philosophy and weights (documentation).

### POST /baseline

Execute baseline evaluation with Groq (llama-3.3-70b-versatile).

Requires: `GROQ_API_KEY` environment variable

## Debugging

### Low Baseline Scores

1. Check `/grader` to understand weights
2. Verify response keywords in data.py (resolve task)
3. Check priority ordering (adjacent = 0.6 credit)

### JSON Parsing Errors

1. Verify action_schema in `/tasks`
2. Check baseline.py prompt building
3. Test with manual action: `curl -X POST http://localhost:8000/step ...`

### Docker Build Issues

```bash
# Rebuild without cache
docker build --no-cache -t customer-support-env .

# Check image
docker run -it customer-support-env /bin/bash
```

## Testing Checklist

- [ ] Dataset verification: `python -c "from customer_support_env.data import TICKETS; print(len(TICKETS))"`
- [ ] Server health: `curl http://localhost:8000/`
- [ ] Tasks endpoint: `curl http://localhost:8000/tasks`
- [ ] Baseline (if GROQ_API_KEY set): `python -m customer_support_env.baseline`
- [ ] Docker build: `docker build -t test . && docker run -p 8000:8000 test`

## Evaluation Criteria

Judges will verify:

1. **Deterministic grading** — Same action + seed always produces same score
2. **Score variance** — Baseline min ≠ max (shows discrimination)
3. **Difficulty ordered** — classify ≥ route ≥ resolve (score-wise)
4. **Reproducibility** — Running baseline twice produces same scores
5. **Documentation** — Field descriptions, reward reasoning, priority rules clear

## Contact & Support

For issues with the framework, see [OpenEnv docs](https://github.com/openai/openenv).

For questions about this environment design, refer to the design philosophy section above.
