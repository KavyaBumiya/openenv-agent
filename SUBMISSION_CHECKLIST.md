# SUBMISSION_CHECKLIST.md

## Pre-Submission Verification Checklist

Use this list to verify everything is ready before submitting to HF Spaces.

---

## 1. Code Completeness

- [ ] **Environment Core**
  - [ ] `customer_support_env/environment.py` - 300+ lines, full grading logic
  - [ ] `customer_support_env/models.py` - Typed Pydantic models (Action, Observation, State, Reward)
  - [ ] `customer_support_env/data.py` - 30+ real customer tickets dataset
  - [ ] `customer_support_env/server/app.py` - FastAPI server with 5+ endpoints

- [ ] **Baseline & Deployment**
  - [ ] `inference.py` - 400+ lines, proper [START]/[STEP]/[END] logging
  - [ ] `Dockerfile` - Multi-stage, production-ready
  - [ ] `requirements.txt` - All dependencies listed
  - [ ] `openenv.yaml` - Complete OpenEnv spec

---

## 2. Functionality Tests

Run these before submission:

```bash
# Test 1: Environment imports
python -c "from customer_support_env.environment import CustomerSupportEnvironment; print('✓')"

# Test 2: Quick episode (30 seconds)
python main.py test

# Test 3: API server responds (5 minutes)
uvicorn customer_support_env.server.app:app --port 7860 &
sleep 2
curl -s http://localhost:7860/health | grep healthy
pkill -f uvicorn

# Test 4: Full inference run (set API first)
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"
export HF_TOKEN="your-api-key"
timeout 120 python inference.py | head -20  # Should show [START] lines
```

- [ ] All tests pass

---

## 3. File Checklist

Required files:

- [ ] `README.md` - with sections: Tasks, Observation Space, Setup, API, Baseline, Deployment
- [ ] `Dockerfile` - uses Python 3.11-slim, exposes port 7860, has HEALTHCHECK
- [ ] `requirements.txt` - includes fastapi, uvicorn, openai, httpx, pydantic
- [ ] `openenv.yaml` - name, version, 3 tasks, reward_config, api section
- [ ] `inference.py` - in project root, executable, proper logging format
- [ ] `main.py` - entry point with baseline/server/test options
- [ ] `.env.example` - template with API_BASE_URL, MODEL_NAME, HF_TOKEN

Optional but recommended:

- [ ] `DEPLOYMENT.md` - setup instructions
- [ ] `.gitignore` - excludes .env, __pycache__, *.pyc, .venv/
- [ ] `tests/` - unit tests for environment

---

## 4. OpenEnv Spec Validation

Run this command:

```bash
pip install openenv-core
openenv validate
```

Expected output:
```
✓ openenv.yaml is valid
✓ customer_support_env: spec OK
```

Checklist:
- [ ] `openenv validate` passes
- [ ] `openenv.yaml` has all required keys
- [ ] `tasks` section has 3+ tasks with difficulty: [easy, medium, hard]
- [ ] `reward_config` defines reward range [0.0, 1.0]
- [ ] All action schemas have `required` and `enum` constraints

---

## 5. API Endpoint Verification

Start server and test each endpoint:

```bash
# GET /health
curl http://localhost:7860/health
# Expected: {"status": "healthy"}

# GET /tasks
curl http://localhost:7860/tasks
# Expected: Array of 3 task objects

# GET /grader
curl http://localhost:7860/grader
# Expected: Reward config with weights

# POST /reset
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "classify", "seed": 0}'
# Expected: {"session_id": "...", "observation": {...}}

# POST /step
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc", "category": "billing", "priority": "high"}'
# Expected: {"observation": {...}, "reward": 0.5, "done": false, "info": {...}}

# GET /state
curl http://localhost:7860/state?session_id=abc
# Expected: {"episode_id": "...", "step_count": 1, ...}
```

Checklist:
- [ ] All 5 endpoints return HTTP 200
- [ ] /reset returns valid session_id and observation
- [ ] /step returns observation, reward, done, info
- [ ] /state returns episode state
- [ ] No errors in logs

---

## 6. Inference Script Verification

```bash
# Setup
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"
export HF_TOKEN="hf_xxxxxxxxxxxx"

# Run full baseline
timeout 180 python inference.py > baseline_output.txt 2>&1

# Check output format
grep "\[START\]" baseline_output.txt | wc -l  # Should be 9 (3 tasks × 3 seeds)
grep "\[STEP\]" baseline_output.txt | wc -l   # Should be 9+ (at least 1 per episode)
grep "\[END\]" baseline_output.txt | wc -l    # Should be 9 (one per episode)

# Check JSON output
cat baseline_scores.json | jq .
# Should have task_scores for classify, route, resolve
```

Checklist:
- [ ] Produces 9 episodes (3 tasks × 3 seeds)
- [ ] Output follows [START]/[STEP]/[END] format exactly
- [ ] baseline_scores.json is created
- [ ] Each task has mean_episode_score and episode_rewards
- [ ] Scores are in [0.0, 1.0] range
- [ ] Completes in < 20 minutes

---

## 7. Docker Build Verification

```bash
# Build image
docker build -t customer-support-env .

# Verify build succeeded (exit code 0)
echo $?

# Run container
docker run -p 7860:7860 \
  -e API_BASE_URL="https://router.huggingface.co/v1" \
  -e MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct" \
  -e HF_TOKEN="hf_xxxxxxxxxxxx" \
  customer-support-env &

# Wait for startup
sleep 5

# Test health
curl -s http://localhost:7860/health | grep healthy

# Kill container
pkill -f "docker run"
```

Checklist:
- [ ] Docker build succeeds (exit code 0)
- [ ] Container starts without errors
- [ ] /health responds within 5 seconds
- [ ] No memory issues or crashes

---

## 8. HF Spaces Deployment

Before submitting:

1. [ ] GitHub repo is public and up-to-date
2. [ ] All files committed and pushed
3. [ ] Space created and linked
4. [ ] Secrets set: API_BASE_URL, MODEL_NAME, HF_TOKEN
5. [ ] Docker build completed (check Space Activity)
6. [ ] App tab shows "Running" status
7. [ ] Test Space API:
   ```bash
   curl https://YOUR_USERNAME-customer-support-env.hf.space/health
   # Should return {"status": "healthy"}
   ```

Checklist:
- [ ] Space builds successfully
- [ ] Space is running (green status)
- [ ] /health returns 200 with 5 seconds
- [ ] No build warnings/errors

---

## 9. Documentation

Verify README and other docs are complete:

- [ ] README has clear motivation and real-world use case
- [ ] Tasks section explains classify → route → resolve progression
- [ ] Reward design explains grading criteria and penalties
- [ ] Setup instructions work end-to-end (copy/paste should work)
- [ ] API Reference documents all 5+ endpoints
- [ ] Baseline section explains expected scores
- [ ] Deployment section has HF Spaces instructions
- [ ] DEPLOYMENT.md has troubleshooting guide

Checklist:
- [ ] README is comprehensive (2000+ words)
- [ ] All links are working
- [ ] All code examples are correct
- [ ] No TODOs or placeholder text remaining

---

## 10. Final Submission Steps

```bash
# 1. Run full validation
chmod +x scripts/validate-submission.sh
./scripts/validate-submission.sh https://YOUR_SPACE_URL .

# 2. Check one more time
python -c "
import yaml
with open('openenv.yaml') as f:
    spec = yaml.safe_load(f)
    print(f'Tasks: {len(spec[\"tasks\"])}')
    print(f'Version: {spec[\"version\"]}')
    print('✓ Ready to submit')
"

# 3. Commit and push
git add -A
git commit -m "Final submission: customer-support-env"
git push
```

Final checks:
- [ ] validator script passes all 3 checks
- [ ] openenv.yaml is valid YAML with correct structure
- [ ] All files pushed to GitHub and HF Space
- [ ] Space shows "Running" status
- [ ] No uncommitted changes

---

## Expected Baseline Performance

With meta-llama/Llama-3.1-8B:
- **Classify (Easy)**: 0.65–0.80 mean score
- **Route (Medium)**: 0.45–0.65 mean score  
- **Resolve (Hard)**: 0.35–0.55 mean score

Scores vary with:
- Model size (larger = higher)
- Temperature (0.0 deterministic, higher = varied)
- API endpoint/implementation

---

## Disqualification Risks

- [ ] Space doesn't deploy or doesn't respond to /reset
- [ ] Missing graders or graders always return same score
- [ ] No baseline inference script or script doesn't run
- [ ] Less than 3 tasks or tasks aren't differentiated
- [ ] openenv validate fails
- [ ] Docker doesn't build
- [ ] Plagiarism or trivial modification of existing environments

---

**Completion Date**: 

Completed by: _________________________

Status: ☐ Ready to Submit  |  ☐ Needs Fixes  |  ☐ In Progress
