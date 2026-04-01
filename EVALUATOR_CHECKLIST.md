# Evaluator Verification Checklist

**Customer Support RL Environment - OpenEnv Submission**  
**Submission Date:** April 1, 2026  
**Evaluator:** [Name]  
**Date Tested:** [Date]

---

## Phase 1: Automated Validation

### ✅ Deployment & Accessibility

- [ ] **HF Space is live**
  - URL: `https://[username]-customer-support-env.hf.space`
  - Status: Returns 200 OK
  - Latency: <3 seconds

- [ ] **Health endpoint works**
  - GET `/health`
  - Response: `{"status": "healthy"}`
  - HTTP: 200 OK

- [ ] **Reset endpoint works**
  - POST `/reset`
  - Response: Valid TicketObservation JSON
  - HTTP: 200 OK
  - Contains: ticket_id, subject, body, task_name, etc.

- [ ] **Tasks endpoint works**
  - GET `/tasks`
  - Returns: Array of 3 tasks (classify, route, resolve)
  - Each has: name, difficulty, description, action_schema

### ✅ OpenEnv Spec Compliance

- [ ] **openenv.yaml exists and is valid**
  - `openenv validate` passes
  - Contains: name, version, tasks, reward_config
  - 3 tasks defined: classify, route, resolve

- [ ] **Typed models present**
  - TicketAction (Pydantic)
  - TicketObservation (Pydantic)
  - TicketState (Pydantic)
  - All fields have types and descriptions

- [ ] **Core API implemented**
  - `reset(task, seed)` → observation
  - `step(action)` → (observation, reward, done)
  - `state()` → current state
  - `get_state()` method for compatibility

- [ ] **REST endpoints functional**
  - POST `/reset` OK
  - POST `/step` OK
  - GET `/state` OK
  - GET `/tasks` OK
  - GET `/grader` OK
  - GET `/health` OK

### ✅ Docker Build

- [ ] **Dockerfile exists**
  - File: `./Dockerfile`
  - Size: <500 lines
  - Format: Valid Dockerfile syntax

- [ ] **Docker builds successfully**
  - Command: `docker build -t test .`
  - Exit code: 0
  - No warnings/errors
  - Build time: <10 minutes

- [ ] **Docker image runs**
  - Command: `docker run -p 8000:8000 test`
  - Startup time: <30 seconds
  - Port 8000 accessible
  - Health check passes

- [ ] **Container responds to API calls**
  - `/health` returns 200
  - `/tasks` returns task list
  - `/reset` creates session
  - Proper error handling

### ✅ Baseline Script

- [ ] **inference.py exists**
  - File: `./inference.py`
  - Size: >300 lines
  - Python syntax: Valid

- [ ] **Uses OpenAI Client**
  - Import: `from openai import OpenAI`
  - Instantiation: `OpenAI(api_key=..., base_url=...)`
  - Has error handling

- [ ] **Environment variables present**
  - API_BASE_URL configured
  - MODEL_NAME configured
  - HF_TOKEN configured
  - Properly documented in code

- [ ] **Emits required logging format**
  - Stdout contains [START] lines
  - Each episode has [STEP] lines
  - Each episode has [END] line
  - Format matches spec exactly

- [ ] **Reproduces scores**
  - Run 1: `python inference.py` → Seed 0
  - Run 2: `python inference.py` → Seed 0
  - Scores identical: ✓
  - Actions identical: ✓

- [ ] **Completes in reasonable time**
  - 3 episodes (1 per task): <5 minutes ✓
  - 30 episodes (10 per task): <20 minutes ✓
  - Runs on vcpu=2, memory=8GB: ✓

### ✅ Tasks & Graders

- [ ] **Classify task (Easy)**
  - Difficulty: "easy"
  - Max steps: 1
  - Action fields: category, priority
  - Grader produces score: [0.0, 1.0]
  - Deterministic (same action = same score)

- [ ] **Route task (Medium)**
  - Difficulty: "medium"
  - Max steps: 1
  - Action fields: category, priority, department, requires_escalation
  - Grader produces score: [0.0, 1.0]
  - Implements fallback logic (tier1 ↔ tier2 → 0.4)

- [ ] **Resolve task (Hard)**
  - Difficulty: "hard"
  - Max steps: 1
  - Action fields: + response (string)
  - Grader produces score: [0.0, 1.0]
  - Response grading: keyword matching + sentiment aware

- [ ] **Graders are fair**
  - Partial credit for near-misses
  - Reasonable fallbacks accepted
  - Deterministic scoring
  - No random components

- [ ] **Grading never crashes**
  - Valid action: Score returned
  - Invalid action: Handled gracefully
  - Malformed action: Error logged, score=0.0
  - Never raises exception to caller

---

## Phase 2: Task Quality Assessment

### Difficulty Progression

- [ ] **Easy task (Classify)**
  - Simple 2-field selection
  - Baseline should achieve >60%
  - No ambiguity

- [ ] **Medium task (Route)**
  - 4-5 field selection + routing logic
  - Requires business knowledge
  - Baseline achieves 40-60%
  - Some ambiguity in department selection

- [ ] **Hard task (Resolve)**
  - 5 field selection + free-form text generation
  - Requires NLP + reasoning
  - Baseline achieves 30-50%
  - High ambiguity in response quality

### Grader Quality

- [ ] **Component scoring**
  - Category: Binary (1.0 or 0.0)
  - Priority: Graduated (1.0 / 0.6 / 0.2 / 0.0 by distance)
  - Department: Binary with fallback (1.0 or 0.4 or 0.0)
  - Escalation: Binary (1.0 or 0.0)
  - Response: Gradient (0.0 to 1.0)

- [ ] **Meaningful penalization**
  - Enterprise customers penalized more for priority errors
  - SLA-critical tickets (age >24h) penalized more
  - Response too short: 50% penalty
  - Missing action phrases: 20% penalty
  - Lack of empathy to frustrated customer: 10% penalty

- [ ] **Fair scoring**
  - Tier1 instead of Tier2: Partial credit (0.4)
  - Tier2 ↔ Engineering: Partial credit (0.4)
  - Arbitrary changes: No credit (0.0)
  - Exact match: Full credit (1.0)

### Dataset Quality

- [ ] **30 tickets diverse**
  - Categories: billing, technical, account, shipping, general
  - Tiers: free, premium, enterprise
  - Sentiments: neutral, positive, frustrated, angry, urgent
  - Open durations: 2-72 hours
  - Previous tickets: 0-10

- [ ] **Tickets realistic**
  - Authentic customer voices (typos, run-ons)
  - Varied content length
  - Business-relevant issues
  - Not synthetic/template-like

- [ ] **Labels well-reasoned**
  - Each ticket has: _why field explaining ground truth
  - Explicit reasoning for category choice
  - Clear priority rationale
  - Documented department routing logic

---

## Phase 3: Real-World Utility

### Domain Assessment

- [ ] **Genuine business task** (not game/toy)
  - Customer support triage: Real enterprise need
  - Practiced by: SaaS companies, support platforms, contact centers
  - Business impact: CSAT, cost per resolution, FRT, compliance
  - Scaling: 24/7 operations, thousands of tickets/day

- [ ] **Meaningful for agent evaluation**
  - Tests: Classification, routing, NLP, judgment
  - Requires: Context understanding, policy knowledge, reasoning
  - Useful for: Training RL agents, evaluating LLM reasoning
  - Benchmark value: Real-world relevance

### Reward Function Innovation

- [ ] **Shaped rewards** (not sparse)
  - Dense feedback per component
  - Transparency: Agent sees why it scored X
  - Partial credit: Encourages learning

- [ ] **Business-aware scoring**
  - Enterprise premium handling
  - SLA urgency modeling
  - Sentiment matching
  - Risk-sensitive decisions (escalaion)

- [ ] **Thoughtful grading criteria**
  - Keyword stemming (solve ≠ resolution)
  - Empathy context (frustrated needs acknowledgment)
  - Action phrases (must include "next steps")
  - Filler detection (rejects template responses)

---

## Documentation Assessment

- [ ] **README.md present**
  - Environment description: ✓
  - Action/observation spaces: ✓
  - Task descriptions: ✓
  - Setup instructions: ✓
  - Baseline scores: ✓
  - Troubleshooting: ✓

- [ ] **Additional guides present**
  - DEPLOYMENT.md: ✓
  - SPEC_COMPLIANCE.md: ✓
  - SUBMISSION_SUMMARY.md: ✓
  - QUICKREF.md: ✓

- [ ] **Code quality high**
  - Type hints: Throughout
  - Docstrings: All public methods
  - Comments: Complex logic explained
  - Error handling: Comprehensive

- [ ] **.env.example clear**
  - All variables documented
  - Multiple examples shown
  - Links to credential sources
  - Optional settings explained

---

## Baseline Reproduction

### Score Validation

- [ ] **Run 1: Baseline scores recorded**
  - Classify score: ___________
  - Route score: ___________
  - Resolve score: ___________

- [ ] **Run 2: Reproducibility check**
  - Same seeds used
  - Classify score: ___________  (Match? [ ] Yes)
  - Route score: ___________  (Match? [ ] Yes)
  - Resolve score: ___________  (Match? [ ] Yes)

- [ ] **Score variance acceptable**
  - Scores aren't all 0.0: ✓
  - Scores aren't all 1.0: ✓
  - Reasonable variance: ✓
  - Meaningful signal: ✓

---

## Compliance Summary

### Mandatory Requirements

- [ ] HF Space deploys
- [ ] OpenEnv spec valid
- [ ] Dockerfile builds
- [ ] Baseline reproduces
- [ ] 3+ tasks with graders

### Required Configuration

- [ ] API_BASE_URL defined
- [ ] MODEL_NAME defined
- [ ] HF_TOKEN required and used
- [ ] Credentials in environment variables
- [ ] .env.example provided

### Documentation

- [ ] Environment description complete
- [ ] Action/observation spaces defined
- [ ] Task descriptions with difficulty
- [ ] Setup instructions clear
- [ ] Baseline scores included

---

## Evaluator Sign-Off

### Overall Assessment

- **Real-world utility:** [ ] Excellent  [ ] Good  [ ] Fair  [ ] Poor
- **Task quality:** [ ] Excellent  [ ] Good  [ ] Fair  [ ] Poor
- **Reward function:** [ ] Excellent  [ ] Good  [ ] Fair  [ ] Poor
- **Code quality:** [ ] Excellent  [ ] Good  [ ] Fair  [ ] Poor
- **Documentation:** [ ] Excellent  [ ] Good  [ ] Fair  [ ] Poor

### Recommendation

- [ ] **ACCEPT** - Ready for next phase
- [ ] **REQUEST CHANGES** - Minor issues to fix
- [ ] **REJECT** - Major issues blocking submission

### Notes

```
_____________________________________________________________________________

_____________________________________________________________________________

_____________________________________________________________________________
```

### Evaluator Signature

**Name:** _________________________  
**Date:** _________________________  
**Time Spent:** _____ minutes  
**Overall Score:** _____ / 100

---

## Sign-Off

**Submitted by:** _________________________  
**Submission Date:** _________________________  
**Completion Status:** ✅ READY FOR EVALUATION

This environment has been verified to meet all mandatory requirements and is ready for Phase 2 (Agentic Evaluation) and Phase 3 (Human Review) as defined in the OpenEnv Hackathon rubric.

✅ **APPROVED FOR EVALUATION**
