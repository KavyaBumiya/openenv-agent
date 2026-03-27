# Project State Analysis Report
**Generated**: March 27, 2026  
**Focus**: Identifying exact mismatches between documentation and implementation

---

## 1. RESOLVE TASK REWARD WEIGHTS — CRITICAL MISMATCH

### 📄 OpenEnv YAML (openenv.yaml)
**File**: [openenv.yaml](openenv.yaml#L90-L95)  
**Lines 90-95**:
```yaml
resolve:
  weights:
    category: 0.2
    priority: 0.15
    department: 0.15
    escalation: 0.1
    response: 0.4
  scaling: normalized
```

**Documented composition**: 0.2 + 0.15 + 0.15 + 0.1 + 0.4 = **1.0 ✓**

### 🔧 Environment Implementation (environment.py)
**File**: [customer_support_env/environment.py](customer_support_env/environment.py#L33-L38)  
**Lines 33-38**:
```python
REWARD_WEIGHTS = {
    "classify": {"category": 0.6, "priority": 0.4},
    "route": {"category": 0.35, "priority": 0.25, "department": 0.25, "escalation": 0.15},
    "resolve": {"category": 0.2, "priority": 0.15, "department": 0.2, "escalation": 0.15, "response": 0.3},
}
```

**Actual resolve weights**: 0.2 + 0.15 + 0.2 + 0.15 + 0.3 = **1.0 ✓ (but different distribution)**

### ⚠️ MISMATCH DETAILS

| Component | openenv.yaml (DOCUMENTED) | environment.py (ACTUAL) | Difference |
|-----------|---------------------------|------------------------|-----------|
| category | 0.2 | 0.2 | ✓ Match |
| priority | 0.15 | 0.15 | ✓ Match |
| **department** | **0.15** | **0.2** | ❌ +0.05 in code |
| **escalation** | **0.1** | **0.15** | ❌ +0.05 in code |
| **response** | **0.4** | **0.3** | ❌ -0.1 in code |

**Impact**: Response quality is weighted 30% (not 40% claimed in docs). Department and escalation are over-weighted.

### 📋 Supporting Evidence from /grader Endpoint
**File**: [customer_support_env/server/app.py](customer_support_env/server/app.py#L97-L108)  
**Lines 97-108** (resolve section):
```python
"resolve": {
    "components": {
        "category": {"weight": 0.2, ...},
        "priority": {"weight": 0.15, ...},
        "department": {"weight": 0.15, ...},
        "escalation": {"weight": 0.1, ...},
        "response": {"weight": 0.4, ...},
    },
    "total_weight": 1.0,
},
```

**The /grader endpoint documents openenv.yaml weights (0.15, 0.1, 0.4)**, NOT the actual code weights (0.2, 0.15, 0.3).

---

## 2. /GRADER ENDPOINT RESPONSE SCHEMA

### 📋 Documented Response Structure
**File**: [customer_support_env/server/app.py](customer_support_env/server/app.py#L63-L148)  
**Lines 63-148**

The `/grader` endpoint returns:
```json
{
  "scoring_philosophy": "string",
  "tasks": {
    "classify": {
      "components": {
        "<metric>": {
          "weight": number,
          "description": string
        }
      },
      "total_weight": 1.0
    }
  },
  "response_grading_criteria": {
    "method": "Keyword presence",
    "logic": "Response must contain at least 75% of required keywords..."
  }
}
```

**Key claim** (Lines 132-138):
```python
"response_grading_criteria": {
    "method": "Keyword presence",
    "logic": "Response must contain at least 75% of required keywords (minimum 3). Scoring: all keywords=1.0, most=0.6, half=0.3, few=0.0. Keywords represent essential response elements: acknowledgment, solution/timeline, professional tone.",
}
```

---

## 3. /STEP ENDPOINT REQUEST/RESPONSE SCHEMA

### 📋 Request Model
**File**: [customer_support_env/server/app.py](customer_support_env/server/app.py#L41-L49)  
**Lines 41-49**:
```python
class StepRequest(BaseModel):
    category: str
    priority: str
    department: Optional[str] = None
    requires_escalation: Optional[bool] = None
    response: Optional[str] = None
```

### 📋 Response Structure
**File**: [customer_support_env/server/app.py](customer_support_env/server/app.py#L193-L219)  
**Lines 193-219** (step endpoint):
```python
@app.post("/step")
async def step(req: StepRequest):
    """Submit action and receive reward.
    
    Returns:
        TicketObservation with reward, feedback, done flag.
    """
    try:
        action = TicketAction(...)
        obs = _env.step(action)
        return obs.model_dump()
```

**Returns**: `TicketObservation.model_dump()` which includes:
- `done` (bool): Always True for single-turn
- `reward` (float): Score in [0.0, 1.0]
- `feedback` (str): Human-readable explanation
- `observation` (nested dict): All ticket fields

---

## 4. CLIENT._PARSE_RESULT METHOD & RESPONSE STRUCTURE

### 📋 Method Implementation
**File**: [customer_support_env/server/client.py](customer_support_env/server/client.py#L27-L47)  
**Lines 27-47**:
```python
def _parse_result(self, payload: dict) -> StepResult:
    """Reconstruct TicketObservation from server's JSON response.
    
    The server returns JSON. We rebuild our typed TicketObservation.
    For missing fields, we use safe defaults (empty string for text, None for optional).
    """
    obs_data = payload.get("observation", {})
    
    observation = TicketObservation(
        done=payload.get("done", False),
        reward=payload.get("reward"),
        ticket_id=obs_data.get("ticket_id", ""),
        subject=obs_data.get("subject", ""),
        body=obs_data.get("body", ""),
        sender_tier=obs_data.get("sender_tier", ""),
        open_since_hours=obs_data.get("open_since_hours", 0),
        sentiment=obs_data.get("sentiment", "neutral"),
        task_name=obs_data.get("task_name", "classify"),
        task_description=obs_data.get("task_description", ""),
        action_schema=obs_data.get("action_schema", "{}"),
        policy_excerpt=obs_data.get("policy_excerpt", ""),
        feedback=obs_data.get("feedback", ""),
        previous_tickets=obs_data.get("previous_tickets", 0),
    )
    
    return StepResult(
        observation=observation,
        reward=payload.get("reward", 0.0),
        done=payload.get("done", False),
    )
```

**Expected Response Structure**:
```json
{
  "done": bool,
  "reward": float,
  "observation": {
    "ticket_id": string,
    "subject": string,
    "body": string,
    "sender_tier": string,
    "open_since_hours": integer,
    "sentiment": string,
    "task_name": string,
    "task_description": string,
    "action_schema": string,
    "policy_excerpt": string,
    "feedback": string,
    "previous_tickets": integer
  }
}
```

---

## 5. ENVIRONMENT._SCORE_RESOLVE METHOD & WEIGHTS APPLIED

### 📋 Method Location and Weights
**File**: [customer_support_env/environment.py](customer_support_env/environment.py#L300-L350)  
**Lines 300-350** (_grade method with resolve logic):
```python
else:  # resolve (HARD task)
    weights = self.REWARD_WEIGHTS["resolve"]
    final_score = (
        cat_score * weights["category"]
        + pri_score * weights["priority"]
        + dept_score * weights["department"]
        + escalation_score * weights["escalation"]
        + resp_score * weights["response"]
    )
    
    # HARD task penalty: missing/inadequate response significantly hurts overall score
    if not response or len(response) < 20:
        final_score *= 0.5  # 50% penalty for incomplete resolve attempts

return round(final_score, 3)
```

### ⚠️ ACTUAL WEIGHTS USED IN _GRADE()

**File**: [customer_support_env/environment.py](customer_support_env/environment.py#L33-L38)  
**Lines 33-38**:
```python
"resolve": {"category": 0.2, "priority": 0.15, "department": 0.2, "escalation": 0.15, "response": 0.3},
```

**Formula applied**:
```
final_score = (category × 0.2) + (priority × 0.15) + (department × 0.2) + (escalation × 0.15) + (response × 0.3)
```

**Additional penalty (Lines 346-348)**:
```python
if not response or len(response) < 20:
    final_score *= 0.5  # 50% penalty
```

---

## 6. DATASET LABELS FOR TKT-003 & TKT-023

### TKT-003: Downgrade Request
**File**: [customer_support_env/data.py](customer_support_env/data.py#L47-L59)  
**Lines 47-59**:

```python
{
    "id": "TKT-003",
    "subject": "Can I downgrade to a cheaper plan",
    "body": "I've been on the Pro plan for 8 months but I realize I don't use all the features. Can I switch to the basic plan instead? Will I get a refund for the difference in this billing cycle?",
    "tier": "free",
    "category": "billing",
    "priority": "low",
    "department": "tier1",
    "previous_tickets": 0,
    "requires_escalation": False,
    "open_since_hours": 15,
    "sentiment": "neutral",
    "response_keywords": ["process", "refund", "downgrade", "effective"],
    "_why": "Billing question but not urgent. Free tier user, simple question. Tier1 can handle this (it's a FAQ). Low priority.",
}
```

**Labels**:
- **Priority**: `"low"` ✓
- **_why**: "Billing question but not urgent. Free tier user, simple question. Tier1 can handle this (it's a FAQ). Low priority."

---

### TKT-023: Documentation Feedback
**File**: [customer_support_env/data.py](customer_support_env/data.py#L298-L312)  
**Lines 298-312**:

```python
{
    "id": "TKT-023",
    "subject": "Documentation typo/improvement suggestion",
    "body": "In the API docs section 3.2, there's a typo: 'reciever' should be 'receiver'. Also, the example could be clearer if you showed error handling. Just wanted to flag this!",
    "tier": "free",
    "category": "general",
    "priority": "medium",
    "department": "tier1",
    "previous_tickets": 2,
    "requires_escalation": False,
    "open_since_hours": 8,
    "sentiment": "positive",
    "response_keywords": ["documentation", "typo", "feedback", "thanks"],
    "_why": "Feedback on docs quality. General, low priority. Tier1 forwards to doc team.",
}
```

**Labels**:
- **Priority**: `"medium"` ✓
- **_why**: "Feedback on docs quality. General, low priority. Tier1 forwards to doc team."
- ⚠️ **Inconsistency**: _why says "low priority" but priority field is "medium"

---

## 7. README.md & README_PRODUCTION.md CLAIMS

### Provider & Baseline Scores
**File**: [README.md](README.md#L55-L80)  
**Lines 55-80**:
```markdown
### EASY: Classify
Baseline: 69.6% accuracy

### MEDIUM: Route
Baseline: 62.5% accuracy

### HARD: Resolve
Baseline: 53.8% accuracy
```

**File**: [README.md](README.md#L36)  
**Line 36**: Documented as model evaluation against **Groq Llama-3.3-70b** (from baseline)

### Episodes Per Task
**File**: [README.md](README.md#L55-L80)  
**Lines 31-34** (in /tasks descriptions):
```markdown
| Task | Score | Min | Max | Variance |
|------|-------|-----|-----|----------|
| Classify | **69.6%** | 24% | 100% | ✓ Meaningful |
| Route | **62.5%** | 15% | 100% | ✓ Meaningful |
| Resolve | **53.8%** | 25% | 88% | ✓ Meaningful |
```

Implies **10 episodes per task** (30 total tickets × 1 episode each)

### "Production-Ready" Language
**File**: [README.md](README.md#L1)  
**Line 1** (title): "A **production-grade OpenEnv reinforcement learning environment**"

**File**: [README_PRODUCTION.md](README_PRODUCTION.md#L1)  
**Line 1**: "A **production-grade OpenEnv reinforcement learning environment**"

**File**: [README.md](README.md#L103)  
**Line 103**: "**Status**: ✅ Production-ready | **Updated**: March 2026"

---

## 8. BASELINE RESULTS — COMPLETE BREAKDOWN

### Documented Baseline (README.md)
**File**: [README.md](README.md#L62-L73)  
**Lines 62-73**:
```markdown
| Task | Score | Min | Max | Variance |
|------|-------|-----|-----|----------|
| Classify | **69.6%** | 24% | 100% | ✓ Meaningful |
| Route | **62.5%** | 15% | 100% | ✓ Meaningful |
| Resolve | **53.8%** | 25% | 88% | ✓ Meaningful |
| **Overall** | **62.0%** | 15% | 100% | |

**Key insight**: Similar scores across tasks = classification is the bottleneck, not task complexity 🎯
```

### Baseline Environment Configuration
**File**: [README_PRODUCTION.md](README_PRODUCTION.md#L174-L186)  
**Lines 174-186**:
```markdown
**Model**: Groq Llama-3.3-70b-versatile  
**Prompting**: Zero-shot (no examples)  
**Episodes**: 30 total (10 × 3 tasks)

| Task | Mean | Min | Max | Std |
|------|------|-----|-----|-----|
| Classify | 69.6% | 24% | 100% | 0.372 |
| Route | 62.5% | 15% | 100% | 0.371 |
| Resolve | 53.8% | 25% | 88% | 0.182 |
| **Overall** | **62.0%** | 15% | 100% | - |
```

---

## 9. SUMMARY TABLE: KEY MISMATCHES

| Category | Documented (Docs) | Actual (Code) | File References | Impact |
|----------|-------------------|---------------|------------------|--------|
| **Resolve department weight** | 0.15 | 0.2 | openenv.yaml:93 vs environment.py:36 | Score differs by ±0.05 per ticket |
| **Resolve escalation weight** | 0.1 | 0.15 | openenv.yaml:94 vs environment.py:36 | Score differs by ±0.05 per ticket |
| **Resolve response weight** | 0.4 | 0.3 | openenv.yaml:95 vs environment.py:36 | CRITICAL: Response 25% less valuable |
| **/grader response schema** | Documents 0.15/0.1/0.4 | Code uses 0.2/0.15/0.3 | app.py:97-108 vs environment.py:36 | /grader returns wrong weights |
| **TKT-023 priority label** | _why says "low" | Field says "medium" | data.py:308 vs data.py:304 | Inconsistent ground truth |
| **Production-ready claim** | "Production-grade" | Weights mismatched, TKT-023 ambiguous | README.md:1, README_PRODUCTION.md:1 | Questionable for final eval |

---

## 10. CRITICAL FINDINGS

### 🔴 BLOCKER: Resolve Weights Discrepancy
- **openenv.yaml** (source of truth for external consumers): `{category: 0.2, priority: 0.15, department: 0.15, escalation: 0.1, response: 0.4}`
- **environment.py** (actual grading logic): `{category: 0.2, priority: 0.15, department: 0.2, escalation: 0.15, response: 0.3}`
- **Impact**: Any external agent or evaluator reading openenv.yaml and openenv.yaml in /grader endpoint will expect response to be worth 40% of resolve score, but actual code only grants 30% (25% less reward for good responses)
- **Affects**: Baseline scores, agent training, task difficulty calibration

### 🟡 ISSUE: TKT-023 Ground Truth Inconsistent
- _why field claims "low priority" but priority field is "medium"
- Could confuse agents learning from this ticket
- Affects dataset reliability for training

### 🟡 ISSUE: /grader Endpoint Returns Wrong Weights
- /grader returns weights from openenv.yaml (0.15/0.1/0.4 for resolve)
- But environment._grade() uses different weights (0.2/0.15/0.3 for resolve)
- External consumers would be misled about actual scoring

---

## 11. RECOMMENDATIONS

1. **Immediately align** environment.py weights with openenv.yaml (or vice versa)
   - Decide which is correct (docs or code)
   - Update the other to match
   - Update /grader response accordingly

2. **Fix TKT-023**: Update _why to say "medium priority" or change priority to "low"

3. **Re-run baseline** after weight fix to validate new baseline scores

4. **Conditional on findings**: Reconsider "production-ready" claim until all discrepancies resolved
