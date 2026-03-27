# 🛠️ ACTIONABLE FIXES - CODE CHANGES NEEDED

## PRIORITY 1: CRITICAL BUGS THE BREAK PRODUCTION

### Bug #1: Global Environment State in app.py
**File:** [server/app.py](server/app.py#L77)
**Severity:** 🔴 CRITICAL - Data corruption risk
**Problem:** All users share one environment instance
**Impact:** User A resets, User B's state corrupted

**Current Code:**
```python
# Line ~70
_env = CustomerSupportEnvironment()
```

**Problem Scenario:**
```
User A: POST /reset (task="classify")
User B: POST /reset (task="route")  
User A: POST /step (with classify action)
User B: POST /step (with route action)
  → User A's action graded against route task!
```

**Fix Required:**
```python
# Remove global _env
# Add session storage

from typing import Dict, Tuple
import uuid

_sessions: Dict[str, Tuple[CustomerSupportEnvironment, TicketObservation]] = {}

@app.post("/reset")
async def reset_environment(request: ResetRequest):
    """Create isolated environment session."""
    session_id = request.session_id or str(uuid.uuid4())
    
    # Create NEW environment for this session
    env = CustomerSupportEnvironment()
    obs = env.reset(
        seed=request.seed,
        episode_id=request.episode_id,
        task=request.task
    )
    
    # Store in session map
    _sessions[session_id] = (env, obs)
    
    return {
        "session_id": session_id,
        "observation": obs.dict()
    }

@app.post("/step")
async def step(request: StepRequest):
    """Process action in session context."""
    session_id = request.session_id
    
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    env, _ = _sessions[session_id]
    
    action = TicketAction(
        category=request.category,
        priority=request.priority,
        department=request.department,
        requires_escalation=request.requires_escalation,
        response=request.response,
    )
    
    obs = env.step(action)
    _sessions[session_id] = (env, obs)
    
    return obs.dict()
```

**Time to Fix:** 2-3 hours

---

### Bug #2: Fragile JSON Extraction in baseline.py
**File:** [baseline.py](baseline.py#L30-L50)
**Severity:** 🔴 CRITICAL - Crashes on malformed input
**Problem:** Multiple JSON extraction attempts don't validate structure

**Current Code:**
```python
def extract_json(text: str) -> dict:
    """Robustly extract JSON from LLM output."""
    if not text:
        raise ValueError("Empty response from LLM")
    
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strip markdown fences
    fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Find outermost JSON - PROBLEM! Too greedy
    brace_match = re.search(r'\{[\s\S]*\}', text)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass
    
    raise ValueError(f"Could not extract valid JSON from: {text[:200]}")
```

**Problems:**
1. Greedy regex `\{[\s\S]*\}` matches first `{` to last `}` (can include garbage)
2. Doesn't validate that extracted JSON has required fields
3. No validation of field types/values
4. Could extract `{"error": "..."}` when we need `{"category": "..."}`

**Fix Required:**
```python
import json
import logging

logger = logging.getLogger(__name__)

def extract_json(text: str, expected_keys: list = None) -> dict:
    """Robustly extract JSON with structure validation.
    
    Args:
        text: Raw LLM response
        expected_keys: List of keys that MUST exist in JSON
        
    Returns:
        Validated JSON dict
        
    Raises:
        ValueError: If JSON cannot be extracted or is invalid
    """
    if not text:
        raise ValueError("Empty response from LLM")
    
    text = text.strip()
    errors = []
    
    # Strategy 1: Direct JSON parse
    try:
        data = json.loads(text)
        _validate_json_structure(data, expected_keys)
        logger.debug(f"Extracted JSON (direct parse)")
        return data
    except (json.JSONDecodeError, ValueError) as e:
        errors.append(f"Direct parse: {e}")
        logger.debug(f"Direct parse failed: {e}")
    
    # Strategy 2: Markdown code fence
    fence_match = re.search(r'```(?:json)?\s+([\s\S]*?)\s+```', text)
    if fence_match:
        try:
            data = json.loads(fence_match.group(1))
            _validate_json_structure(data, expected_keys)
            logger.debug(f"Extracted JSON (markdown fence)")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            errors.append(f"Markdown fence: {e}")
            logger.debug(f"Fence parse failed: {e}")
    
    # Strategy 3: Find JSON objects (non-greedy, try each match)
    # Use non-greedy matching to avoid grabbing too much
    for match in re.finditer(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', text):
        try:
            data = json.loads(match.group())
            _validate_json_structure(data, expected_keys)
            logger.debug(f"Extracted JSON (object search)")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Object match failed: {e}")
            continue
    
    # All strategies failed
    error_msg = f"Could not extract valid JSON. Tried: {'; '.join(errors)}"
    logger.error(f"{error_msg}\nOriginal text: {text[:200]}...")
    raise ValueError(error_msg)


def _validate_json_structure(data: dict, required_keys: list = None) -> None:
    """Validate extracted JSON has required structure.
    
    Args:
        data: Dictionary to validate
        required_keys: List of keys that must exist
        
    Raises:
        ValueError: If validation fails
    """
    if not isinstance(data, dict):
        raise ValueError(f"JSON must be object, got {type(data).__name__}")
    
    if required_keys:
        missing = set(required_keys) - set(data.keys())
        if missing:
            raise ValueError(f"Missing required keys: {missing}")
    
    # Validate that values aren't null
    for key, value in data.items():
        if value is None:
            raise ValueError(f"Key '{key}' cannot be null")


# Usage in run_baseline():
response_text = response.choices[0].message.content

# For classify task: need category + priority
task_required_keys = {
    "classify": ["category", "priority"],
    "route": ["category", "priority", "department"],
    "resolve": ["category", "priority", "department", "response"],
}

try:
    action_dict = extract_json(
        response_text,
        expected_keys=task_required_keys[task]
    )
    action = TicketAction(**action_dict)
except ValueError as e:
    logger.warning(f"Failed to parse response: {e}\nText: {response_text[:100]}")
    errors.append(str(e))
    continue
```

**Time to Fix:** 3-4 hours

---

### Bug #3: Missing Data Validation in data.py
**File:** [data.py](data.py#L1)
**Severity:** 🔴 CRITICAL - Silent failures on corrupt data
**Problem:** No validation that ticket data is complete/valid

**Current Code:**
```python
TICKETS = [
    {
        "id": "TKT-001",
        "subject": "...",
        # etc - no validation!
    },
]
```

**Problem Scenario:**
```python
# Someone accidentally removes a field:
TICKETS[0]["category"] = None  # BUG!

# Environment breaks later, hard to debug
env.step(action)  # Crash with confusing error message
```

**Fix Required:**
```python
"""Customer support ticket dataset: 30 carefully designed tickets."""

import sys
from typing import List, Dict, Any

REQUIRED_TICKET_FIELDS = {
    "id": str,
    "subject": str,
    "body": str,
    "tier": str,
    "category": str,
    "priority": str,
    "department": str,
    "previous_tickets": int,
    "requires_escalation": bool,
    "open_since_hours": int,
    "sentiment": str,
    "response_keywords": list,
}

ALLOWED_VALUES = {
    "tier": ["free", "premium", "enterprise"],
    "category": ["billing", "technical", "account", "shipping", "general"],
    "priority": ["low", "medium", "high", "urgent"],
    "department": ["tier1", "tier2", "billing", "engineering", "management"],
    "sentiment": ["frustrated", "angry", "positive", "neutral", "confused", "urgent"],
}

TICKETS = [
    # ... existing ticket data ...
]

def validate_tickets() -> None:
    """Validate all tickets have required fields with correct types.
    
    Raises:
        ValueError: If any ticket is invalid
    """
    if not TICKETS:
        raise ValueError("TICKETS list is empty")
    
    for idx, ticket in enumerate(TICKETS):
        # Check that it's a dict
        if not isinstance(ticket, dict):
            raise ValueError(f"Ticket {idx}: must be dict, got {type(ticket)}")
        
        # Check all required fields exist
        for field, field_type in REQUIRED_TICKET_FIELDS.items():
            if field not in ticket:
                raise ValueError(f"Ticket {idx} (ID: {ticket.get('id')}): missing required field '{field}'")
            
            value = ticket[field]
            
            # Check type
            if not isinstance(value, field_type):
                raise ValueError(
                    f"Ticket {idx} (ID: {ticket.get('id')}): field '{field}' "
                    f"must be {field_type.__name__}, got {type(value).__name__}"
                )
            
            # Check allowed values
            if field in ALLOWED_VALUES:
                allowed = ALLOWED_VALUES[field]
                if value not in allowed:
                    raise ValueError(
                        f"Ticket {idx} (ID: {ticket.get('id')}): field '{field}' "
                        f"value '{value}' not in allowed: {allowed}"
                    )
        
        # Additional validation
        if len(ticket["subject"].strip()) < 5:
            raise ValueError(f"Ticket {idx}: subject too short")
        
        if len(ticket["body"].strip()) < 20:
            raise ValueError(f"Ticket {idx}: body too short")
        
        if ticket["previous_tickets"] < 0:
            raise ValueError(f"Ticket {idx}: previous_tickets must be >= 0")
        
        if ticket["open_since_hours"] < 0:
            raise ValueError(f"Ticket {idx}: open_since_hours must be >= 0")
        
        if not isinstance(ticket["response_keywords"], list) or len(ticket["response_keywords"]) < 2:
            raise ValueError(f"Ticket {idx}: response_keywords must have >= 2 items")
        
        print(f"✓ Ticket {idx} ({ticket['id']}): Valid")


# RUN VALIDATION AT MODULE LOAD TIME
try:
    validate_tickets()
    print(f"\n✓ All {len(TICKETS)} tickets validated successfully\n")
except ValueError as e:
    print(f"\n❌ TICKET VALIDATION FAILED: {e}\n", file=sys.stderr)
    sys.exit(1)
```

**Time to Fix:** 2 hours

---

## PRIORITY 2: HIGH-IMPACT IMPROVEMENTS

### Issue #4: Magic Numbers Hardcoded in environment.py
**File:** [environment.py](environment.py#L260-L290)
**Severity:** 🟡 HIGH - Hard to tune, brittle
**Problem:** Constants scattered throughout code

**Current Code:**
```python
# Line ~265
if ticket.get("tier") == "enterprise" and distance > 0:
    base_score *= 0.7  # WHERE DID 0.7 COME FROM?

# Line ~275
if open_hours > 24 and distance > 0:  # WHY 24?
    base_score *= 0.85

# Line ~345 (guessing)
if not response or len(response) < 20:  # WHY 20?
    final_score *= 0.5
```

**Fix Required:**
```python
class CustomerSupportEnvironment(Environment):
    """Customer support triage environment with configurable grading."""
    
    # ============= GRADING CONFIGURATION =============
    # All magic numbers moved to class constants for easy tuning
    
    # Enterprise customer handling
    ENTERPRISE_PRIORITY_PENALTY = 0.7  # Penalize enterprise priority misses more
    
    # SLA urgency modeling
    SLA_THRESHOLD_HOURS = 24  # Tickets open > 24h are SLA-critical
    SLA_PENALTY_MULTIPLIER = 0.85  # Apply this multiplier when SLA-critical
    
    # Response quality requirements
    RESPONSE_MIN_LENGTH = 20  # Minimum characters for valid response
    RESPONSE_LENGTH_PENALTY = 0.5  # Penalty multiplier for short response
    RESPONSE_KEYWORD_THRESHOLD = 0.75  # Must match 75% of keywords
    
    # Sentiment bonus
    SENTIMENT_EMPATHY_BONUS = 0.1  # Bonus for sentiment-aware response
    
    def _score_priority(self, predicted: str, actual: str, ticket: Dict[str, Any]) -> float:
        """Score priority with configurable penalties."""
        try:
            pred_idx = self.PRIORITY_ORDER.index(predicted)
            actual_idx = self.PRIORITY_ORDER.index(actual)
            distance = abs(pred_idx - actual_idx)
            
            # Base score from distance
            base_score = [1.0, 0.6, 0.2, 0.0][min(distance, 3)]
            
            # Apply configurable enterprise penalty
            if ticket.get("tier") == "enterprise" and distance > 0:
                base_score *= self.ENTERPRISE_PRIORITY_PENALTY
            
            # Apply configurable SLA penalty
            open_hours = ticket.get("open_since_hours", 0)
            if open_hours > self.SLA_THRESHOLD_HOURS and distance > 0:
                base_score *= self.SLA_PENALTY_MULTIPLIER
            
            return round(base_score, 2)
        except (ValueError, IndexError):
            return 0.0
```

**Time to Fix:** 1-2 hours

---

## PRIORITY 3: MISSING LOGGING

### Issue #5: No Logging Framework
**File:** All Python files
**Severity:** 🟡 HIGH - Debugging nightmare in production
**Problem:** Using `print()` statements, no structured logging

**Add Logging Setup:**

**Create:** `customer_support_env/logging_config.py`
```python
"""Logging configuration for the environment."""

import logging
import sys

def setup_logging(level=logging.INFO):
    """Configure logging for all modules."""
    
    # Root logger
    root = logging.getLogger()
    root.setLevel(level)
    
    # Console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    
    return root

# Module loggers
logger = logging.getLogger('customer_support_env')
```

**Update:** `environment.py`
```python
# Add at top
import logging
logger = logging.getLogger(__name__)

# In _grade() method
def _grade(self, action: TicketAction) -> float:
    logger.debug(f"Grading action for ticket {self._ticket['id']}")
    logger.debug(f"  Category: {action.category} (expected: {self._ticket['category']})")
    logger.debug(f"  Priority: {action.priority} (expected: {self._ticket['priority']})")
    
    # ... grading logic ...
    
    logger.info(f"Final score: {final_score} for ticket {self._ticket['id']}")
    return final_score
```

**Update:** `baseline.py`
```python
# Add at top
import logging
logger = logging.getLogger(__name__)

# In run_baseline()
logger.info(f"Starting baseline: mode={mode}")
for episode in range(len(TICKETS)):
    logger.debug(f"Episode {episode}/{len(TICKETS)}: {task} task")
    
    if error:
        logger.warning(f"Failed to process episode {episode}: {error}")
    else:
        logger.debug(f"Score: {score:.1%}")

logger.info(f"Baseline complete: {final_score:.1%}")
```

**Time to Fix:** 2 hours

---

## PRIORITY 4: ADD INPUT VALIDATION

### Issue #6: No Response Field Validation in models.py
**File:** [models.py](models.py#L50)
**Severity:** 🟠 MEDIUM - Allows invalid input
**Problem:** Response field not validated for length/content

**Fix Required:**
```python
from pydantic import field_validator

@field_validator("response", mode="before")
@classmethod
def _validate_response(cls, value: Optional[str]) -> Optional[str]:
    """Validate response field."""
    if value is None:
        return None
    
    # Convert to string and strip whitespace
    if isinstance(value, str):
        value = value.strip()
    else:
        value = str(value).strip()
    
    # Check length (max 5000 chars)
    if len(value) > 5000:
        raise ValueError(f"Response too long: {len(value)} > 5000 characters")
    
    # Return None if empty after stripping
    return value if value else None

@field_validator("category")
@classmethod
def _normalize_category(cls, value: str) -> str:
    """Normalize category to lowercase."""
    return value.strip().lower() if value else value
```

**Time to Fix:** 1 hour

---

## FINAL SUMMARY TABLE

| Fix # | Issue | File | Priority | Time | Impact |
|-------|-------|------|----------|------|--------|
| 1 | Global _env | app.py | 🔴 CRITICAL | 2-3h | HIGH |
| 2 | JSON extraction | baseline.py | 🔴 CRITICAL | 3-4h | HIGH |
| 3 | Data validation | data.py | 🔴 CRITICAL | 2h | MEDIUM |
| 4 | Magic numbers | environment.py | 🟡 HIGH | 1-2h | MEDIUM |
| 5 | Add logging | All | 🟡 HIGH | 2h | MEDIUM |
| 6 | Input validation | models.py | 🟠 MEDIUM | 1h | LOW |

**Total Time to Fix Critical:** ~10-13 hours
**Total Time for All:** ~11-15 hours

---

**Status:** Ready to implement
**Generated:** March 27, 2026
