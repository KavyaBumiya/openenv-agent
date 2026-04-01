# Deployment Guide - Customer Support RL Environment

**Quick Reference for OpenEnv Hackathon Submission**

---

## 🚀 30-Second Summary

This is a **production-ready OpenEnv environment** for customer support ticket triage with:
- ✅ 3 tasks (classify, route, resolve) with graduated difficulty
- ✅ Full OpenEnv spec compliance
- ✅ Real-world graders (partial credit, enterprise handling, SLA modeling)
- ✅ Baseline `inference.py` script using OpenAI Client
- ✅ Docker-ready, HF Spaces deployable
- ✅ Complete documentation

**Status:** Ready to submit. All checks pass. Deploy in minutes.

---

## Pre-Submission Checklist

### ✅ Core Requirements Met

- [x] Real-world domain (customer support triage)
- [x] 3 tasks: classify (easy), route (medium), resolve (hard)
- [x] Meaningful reward function (0.0–1.0, shaped signals)
- [x] Full OpenEnv spec (typed models, step/reset/state, openenv.yaml)
- [x] Baseline inference with [START], [STEP], [END] logging
- [x] Reproducible scores (seeding works)
- [x] Docker containerized (builds, runs, health checks)
- [x] README with documentation
- [x] Deployment guide

### ✅ Files Checklist

```
✓ inference.py              (Official baseline agent)
✓ requirements.txt          (Dependencies)
✓ Dockerfile                (Container definition)
✓ openenv.yaml              (Spec definition)
✓ README.md                 (Documentation)
✓ .env.example              (Configuration template)
✓ SPEC_COMPLIANCE.md        (Detailed spec check)
✓ DEPLOYMENT.md             (This file)

✓ customer_support_env/
  ✓ models.py               (Typed Pydantic)
  ✓ environment.py          (Core + graders)
  ✓ data.py                 (30 curated tickets)
  ✓ baseline.py             (Groq alternative baseline)
  ✓ openenv_compat.py       (Compatibility layer)
  ✓ server/app.py           (FastAPI server)
  ✓ server/client.py        (WebSocket client)
```

### ✅ Configuration

```
API_BASE_URL=https://router.huggingface.co/v1
MODEL_NAME=meta-llama/Llama-2-7b-chat-hf
HF_TOKEN=hf_your_token_here
```

---

## Getting Started (Local)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment

Copy `.env.example` to `.env` and fill in your LLM credentials:

```bash
# .env file
API_BASE_URL=https://router.huggingface.co/v1
MODEL_NAME=meta-llama/Llama-2-7b-chat-hf
HF_TOKEN=hf_your_token_here
```

Or set via terminal:
```powershell
$env:API_BASE_URL="https://router.huggingface.co/v1"
$env:MODEL_NAME="meta-llama/Llama-2-7b-chat-hf"
$env:HF_TOKEN="hf_your_token_here"
```

### Step 3: Run Baseline

```bash
python inference.py
```

**Expected output (first 15 seconds):**
```
[START] task=classify env=customer_support_env model=meta-llama/Llama-2-7b-chat-hf
[STEP] step=1 action=category=billing, priority=high reward=1.00 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.00

[START] task=route env=customer_support_env model=meta-llama/Llama-2-7b-chat-hf
[STEP] step=1 action=category=billing, priority=high, department=billing, escalation=false reward=0.75 done=true error=null
[END] success=true steps=1 score=0.750 rewards=0.75

[START] task=resolve env=customer_support_env model=meta-llama/Llama-2-7b-chat-hf
[STEP] step=1 action=category=billing, priority=high, department=billing, escalation=false, response=<350 chars> reward=0.85 done=true error=null
[END] success=true steps=1 score=0.850 rewards=0.85
```

---

## Docker Deployment

### Build the Image

```bash
docker build -t customer-support-env:latest .
```

### Run Locally

```bash
docker run \
  -e API_BASE_URL="https://router.huggingface.co/v1" \
  -e MODEL_NAME="meta-llama/Llama-2-7b-chat-hf" \
  -e HF_TOKEN="hf_your_token_here" \
  -p 8000:8000 \
  customer-support-env:latest
```

### Test the Server

```bash
# Health check
curl http://localhost:8000/health

# Get tasks
curl http://localhost:8000/tasks

# Reset episode
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "classify"}'

# Step with action
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "xyz",
    "category": "billing",
    "priority": "high"
  }'
```

---

## Hugging Face Spaces Deployment

### Via GitHub + GitActions (Recommended)

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "OpenEnv submission: customer support environment"
   git push origin main
   ```

2. **Enable HF Spaces sync:**
   - Go to HF Spaces: `https://huggingface.co/spaces/YOUR_USERNAME/customer-support-env`
   - Click "Settings" → sync with GitHub repo
   - Select main branch

3. **HF Spaces auto-deploys:**
   - Watches GitHub push
   - Builds Docker image
   - Launches container
   - API available at: `https://YOUR_USERNAME-customer-support-env.hf.space`

### Manual Deploy

1. Create Space: `https://huggingface.co/spaces?repo_type=space`
2. Choose "Docker" runtime
3. Push repo to HF:
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/customer-support-env
   cd customer-support-env
   cp -r /path/to/this/repo/* .
   git add .
   git commit -m "Initial commit"
   git push
   ```

---

## Validation

### Run OpenEnv Validator

```bash
openenv validate
```

**Expected output:**
```
✓ openenv.yaml is valid
✓ 3 tasks defined
✓ Action/observation schemas defined
✓ Reward configuration present
✓ All required endpoints implemented
```

### Verify Spec Compliance

See [SPEC_COMPLIANCE.md](SPEC_COMPLIANCE.md) for detailed checklist:

```bash
# Quick check
python -c "from customer_support_env.environment import CustomerSupportEnvironment; \
           env = CustomerSupportEnvironment(); \
           obs = env.reset(seed=0, task='classify'); \
           print(f'✓ Environment loaded: {obs.ticket_id}')"
```

---

## Configuration Options

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `API_BASE_URL` | `https://router.huggingface.co/v1` | LLM endpoint |
| `MODEL_NAME` | `meta-llama/Llama-2-7b-chat-hf` | Model to use |
| `HF_TOKEN` | (required) | API authentication |
| `TEMPERATURE` | `0.3` | LLM temperature (lower = deterministic) |
| `MAX_TOKENS` | `500` | Max response length |
| `NUM_SEEDS` | `3` | Seeds per task (3 = 9 total episodes) |

### Edit inference.py for Custom Settings

```python
# In inference.py, modify these constants:

NUM_SEEDS = 30                           # Full benchmark (30 episodes per task)
TEMPERATURE = 0.5                        # Higher = more varied responses
MAX_TOKENS = 1000                        # Longer allowed responses
SUCCESS_SCORE_THRESHOLD = 0.3            # Episode success threshold
```

---

## Baseline Score Reference

With **Hugging Face router + Llama-2-7B model** (temperature 0.3):

| Task | Difficulty | Expected Score |
|------|-----------|-----------------|
| classify | Easy | 0.65–0.75 |
| route | Medium | 0.45–0.60 |
| resolve | Hard | 0.35–0.50 |

**Actual scores vary** based on:
- Model size (larger = better)
- Temperature (lower = more deterministic)
- API endpoint quality

---

## Troubleshooting

### "API token not valid" Error

```
[ERROR] Failed to authenticate. Check API_BASE_URL and HF_TOKEN.
```

**Fix:**
1. Verify token format (should start with `hf_` for HuggingFace)
2. Check token has correct permissions ("Read" minimum)
3. Try with a different endpoint (e.g., switch from HF to Groq)

### "Model not found" Error

```
LLM request error: The model does not exist or you don't have access.
```

**Fix:**
- Verify `MODEL_NAME` is valid for your `API_BASE_URL`
- HF router models: `meta-llama/Llama-2-7b-chat-hf`, etc.
- Groq models: `llama-3.3-70b-versatile`, etc.

### Docker Build Takes Too Long

```
Build context is large, installing dependencies...
```

**Fix:**
- Build uses layer caching (first build is slow, subsequent faster)
- Expected times:
  - Cold build: 3-5 minutes
  - Cached build: <30 seconds

### Low Baseline Scores (All 0.0)

This typically means the LLM isn't producing valid JSON. Check:

1. **Is the API responding?**
   ```bash
   curl $API_BASE_URL/models -H "Authorization: Bearer $HF_TOKEN"
   ```

2. **Can the model generate JSON?**
   Try with a larger model (7B → 70B)

3. **Check the logs:**
   Run `python inference.py` with debug output:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

---

## Performance Tuning

### Speed Up Inference

```python
NUM_SEEDS = 3        # Reduce episodes (default)
TEMPERATURE = 0      # Deterministic mode
MAX_TOKENS = 200     # Shorter responses
```

**Expected runtime:**
- 3 seeds per task: ~30–60 sec
- 30 seeds per task: ~5–15 min
- 100 seeds per task: ~20–50 min

### Improve Baseline Scores

```python
# Use larger, more capable model
MODEL_NAME = "meta-llama/Llama-3-70b-instruct"  # vs 7B default

# Lower temperature for determinism
TEMPERATURE = 0.1    # vs 0.3 default

# More detailed system prompts (edit build_system_prompt in inference.py)
```

---

## Quick Links

| Resource | URL |
|----------|-----|
| OpenEnv Spec | [openenv.yaml](openenv.yaml) |
| Compliance Check | [SPEC_COMPLIANCE.md](SPEC_COMPLIANCE.md) |
| Main README | [README.md](README.md) |
| Baseline Script | [inference.py](inference.py) |
| Configuration | [.env.example](.env.example) |
| Requirements | [requirements.txt](requirements.txt) |

---

## Support

For issues or questions:

1. **Check SPEC_COMPLIANCE.md** — Most common issues documented
2. **Read README.md** — Detailed walkthrough
3. **Review inference.py** — Heavily commented code
4. **Check .env.example** — Configuration reference

---

## Submit

When ready to submit:

1. ✅ Run `python inference.py` and verify output
2. ✅ Run `docker build -t env .` and verify success
3. ✅ Run `openenv validate` and verify pass
4. ✅ Push all files to GitHub
5. ✅ Deploy via HF Spaces GitHub sync
6. ✅ Test `/reset` endpoint returns 200
7. ✅ Submit via evaluation platform

**Total prep time: ~10 minutes**

✅ **Ready to submit!**
