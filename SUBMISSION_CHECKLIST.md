# OpenEnv Hackathon Submission Checklist

**Project:** Customer Support RL Environment  
**Status:** Ready for Submission ✅  
**Last Updated:** April 8, 2026

---

## Phase 1: Automated Validation ✅

### ✅ HF Space Deployment
- **Status:** READY
- **URL:** https://kavyabumiya-customer-support-env.hf.space
- **Verification Method:** Manual ping to `/health` and `/reset` endpoints
- **Action Required:** Ensure Space is running when submitting

### ✅ OpenEnv Spec Compliance
- **openenv.yaml:** ✅ Present and valid
  - 3 tasks: `classify` (easy), `route` (medium), `resolve` (hard)
  - Correct difficulty progression
  - Action schemas defined for all tasks
  - Observation fields documented
  - Reward config with shaped rewards in range [0.001, 0.999]
  
- **Typed Models:** ✅ In place
  - `TicketAction`, `TicketObservation`, `TicketReward` (all Pydantic)
  - Strict (0, 1) bounds enforcement with guards
  
- **API Endpoints:** ✅ All required endpoints
  - `POST /reset` → returns `{session_id, observation}`
  - `POST /step` → returns `{observation, reward, done, info}`
  - `GET /state` → returns current state
  - `GET /health` → health check

### ✅ Dockerfile
- **Status:** Ready
- **Location:** `/Dockerfile` (root)
- **Base:** `python:3.11.9-slim`
- **Entry:** `python server/app.py`
- **Port:** 7860
- **Build Time:** ~60s (expect ≤600s timeout)

### ✅ Baseline Inference Script
- **Status:** Ready
- **Location:** `/inference.py` (root)
- **Language:** Python
- **Required Env Vars:**
  - `API_BASE_URL` (default: HuggingFace router)
  - `MODEL_NAME` (default: Llama-3.1-8B-Instruct)
  - `HF_TOKEN` (required; will be injected by validator)
  
- **Stdout Format:** ✅ SPEC-COMPLIANT
  ```
  [START] task=<task_name> env=customer_support_env model=<model>
  [STEP] step=<n> action=<action_json> reward=<0.0000> done=<true|false> error=<msg|null>
  [END] success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>
  ```
  - ✅ Exactly 3 line types (no extras allowed)
  - ✅ One [START] per episode
  - ✅ One [STEP] per step
  - ✅ One [END] always, even on error
  - ✅ `score` field included (CRITICAL FIX applied)
  - ✅ Rewards formatted to 4 decimals

### ✅ 3+ Tasks with Graders
| Task | Difficulty | Grader | Score Range | Max Steps |
|------|-----------|--------|-------------|-----------|
| classify | Easy | `ClassifyGrader` | (0, 1) | 1 |
| route | Medium | `RouteGrader` | (0, 1) | 2 |
| resolve | Hard | `ResolveGrader` | (0, 1) | 3 |

- ✅ All graders produce scores strictly in (0, 1)
- ✅ Score variance observed: 0.26–0.95 range
- ✅ No hardcoded/constant scores (variance = 0.69)
- ✅ Deterministic and reproducible (seeded)

### ✅ Graders Don't Always Return Same Score
- Test case proof: boundary_condition test shows variance of **0.69**
  - Perfect classification: 0.95
  - Wrong category only: 0.56
  - Wrong priority only: 0.65
  - Both wrong: 0.26

---

## Phase 2: Agentic Evaluation (Post-Submission)

### 📋 What Validator Will Check
1. **Space Ping:** HTTP 200 to `/reset` (3 retries, 30s timeout)
2. **Docker Build:** `docker build` succeeds in ≤600s
3. **openenv validate:** Command-line validator passes
4. **Inference Run:** `python inference.py` completes in <20min
5. **Score Variance:** Graders produce different scores across episodes

### 📋 Performance Expectations
| Component | Expected Result |
|-----------|-----------------|
| Classify baseline | 0.65–0.80 (easy) |
| Route baseline | 0.45–0.65 (medium) |
| Resolve baseline | 0.35–0.55 (hard) |
| Runtime per episode | <2min |
| Total (3 tasks × seeds) | <20min |
| Memory usage | <2GB |

---

## Phase 3: Human Review (If Selected)

### Real-World Utility (30%)
- ✅ Customer support triage is a **genuine enterprise use case**
- ✅ Simulates realistic decision-making (category, priority, routing, response)
- ✅ Applicable to SaaS support teams and ticketing systems

### Task & Grader Quality (25%)
- ✅ **Easy task (Classify):** Single decision, clear grading (0.6 weight on category correctness)
- ✅ **Medium task (Route):** Adds department routing, escalation flag
- ✅ **Hard task (Resolve):** Multi-component (classify + route + write response), response quality weighted at 0.3
- ✅ **Graders deterministic:** Rule-based, no randomness
- ✅ **Difficulty progression:** 1 → 2 → 3 steps; increasing complexity

### Environment Design (20%)
- ✅ **State Management:** Fresh reset per episode, clean ticket selection
- ✅ **Action/Observation Space:** Well-typed Pydantic models
- ✅ **Reward Shaping:** 
  - Partial progress (category, priority, department each scored independently)
  - Graduated priority penalty (0.95 for exact, 0.6 for one step off, 0.2 for two steps)
  - Enterprise customer penalty (context-aware)
  - SLA escalation for old tickets
  - Response quality with keyword + empathy bonus
- ✅ **Episode Length:** Varies (1–3 steps) based on task

### Code Quality & Spec Compliance (15%)
- ✅ **Project Structure:** Clean separation (server/, graders/, models/, data/)
- ✅ **OpenEnv Spec:** Full compliance (`step()`, `reset()`, `state()`, openenv.yaml, typed models)
- ✅ **Documentation:** Comprehensive README with setup, API reference, baseline scores
- ✅ **Error Handling:** Graceful fallbacks (rule-based grader when OpenAI unavailable)
- ✅ **Type Safety:** All Pydantic models with validation
- ✅ **Tested:** Boundary condition tests, HF Spaces validation

### Creativity & Novelty (10%)
- ✅ **Novel Domain:** Customer support RL less common than game environments
- ✅ **Clever Grading:** Multi-component scoring with business context (enterprise tier, SLA, escalation)
- ✅ **Reward Design:** Shaped rewards combining multiple signals
- ✅ **Realistic Tickets:** 30 curated tickets with real-world sentiment, history, and customer tiers

---

## Disqualification Check ✅

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Environment deploys | ✅ PASS | HF Space Live @ https://kavyabumiya-customer-support-env.hf.space |
| Responds to /reset | ✅ PASS | GET logs show 200 OK responses |
| Graders vary | ✅ PASS | Variance = 0.69 (min 0.26, max 0.95) |
| Not hardcoded | ✅ PASS | RuleBasedGrader produces different scores per action |
| Not plagiarized | ✅ PASS | Original customer support env from scratch |
| Has baseline | ✅ PASS | `inference.py` with [START]/[STEP]/[END] format |

---

## Pre-Submission Validation Commands

### Local Testing (Before Submission)
```bash
# 1. Verify Python syntax
python -m py_compile inference.py customer_support_env/server/app.py

# 2. Run boundary condition tests
python test_score_bounds.py

# 3. Build Docker image
docker build -t customer-support-env .

# 4. Test HF Space ping (if deployed)
curl -X POST https://kavyabumiya-customer-support-env.hf.space/reset \
  -H "Content-Type: application/json" -d '{"task": "classify", "seed": 0}'

# 5. Test inference.py
unset OPENAI_API_KEY  # Simulate validator injecting key
export HF_TOKEN="hf_..."
python inference.py 2>&1 | head -10
```

### Validator Will Run
```bash
# HF Space Health Check
curl -s -o /dev/null -w "%{http_code}" -X POST \
  https://kavyabumiya-customer-support-env.hf.space/reset \
  -H "Content-Type: application/json" -d '{"task":"classify","seed":0}'

# Docker Build (≤600s timeout)
docker build .

# openenv validate
openenv validate

# Baseline Inference (<20min)
export HF_TOKEN="..." API_BASE_URL="..." MODEL_NAME="..."
python inference.py
```

---

## Final Checklist Before Commit

- [x] openenv.yaml valid and complete (3 tasks, reward config)
- [x] Dockerfile builds and runs on `python3.11-slim`
- [x] inference.py in root directory
- [x] [START]/[STEP]/[END] stdout format correct (including score)
- [x] All required env vars documented
- [x] README complete (setup, tasks, baseline, API reference)
- [x] HF Space metadata in README frontmatter
- [x] Graders produce scores in (0, 1) — never 0.0 or 1.0
- [x] Score variance confirmed (>0.1 range)
- [x] No secrets in code (uses env vars)
- [x] Git repo clean and pushed

---

## Submission Instructions

1. **Verify HF Space is running:** https://kavyabumiya-customer-support-env.hf.space
2. **Run pre-submission validation:**
   ```bash
   chmod +x scripts/validate-submission.sh
   ./scripts/validate-submission.sh https://kavyabumiya-customer-support-env.hf.space .
   ```
3. **Submit:**
   - Copy repo URL: https://github.com/KavyaBumiya/openenv-agent
   - Fill hackathon form with Space URL and repo URL
   - Submit!

---

## Estimated Scores (Self-Assessment)

| Category | Weight | Expected |
|----------|--------|----------|
| Real-world utility | 30% | 26/30 (customer support is genuine but specific niche) |
| Task & grader quality | 25% | 23/25 (excellent graders, clear difficulty) |
| Environment design | 20% | 18/20 (good reward shaping, clean design) |
| Code quality & spec | 15% | 14/15 (full OpenEnv compliance) |
| Creativity & novelty | 10% | 8/10 (novel domain, interesting grader mechanics) |
| **Total** | **100%** | **89/100** |

---

**Status:** ✅ **READY FOR SUBMISSION**

All automated checks pass. HF Space is live and responsive. Baseline inference script is properly formatted. Ready to submit!
