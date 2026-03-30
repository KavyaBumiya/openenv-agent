# Quick Start: main.py

**main.py** is the single entry point for the entire environment.

## Usage

### Show Help Menu
```bash
python main.py
```

### Run Baseline Evaluation
Evaluates the environment with Groq AI (30 episodes per task = 90 total)
```bash
python main.py baseline
```

**Output includes:**
- Classification accuracy (EASY task)
- Routing accuracy (MEDIUM task)  
- Response generation accuracy (HARD task)
- Difficulty gradient verification

**Requirements:**
- `GROQ_API_KEY` environment variable set
- Groq API access

### Start API Server
Launches FastAPI server with REST and WebSocket endpoints
```bash
python main.py server
```

**Available at:**
- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- WebSocket: `ws://localhost:8000/ws`

**Features:**
- `/reset` - Reset environment
- `/step` - Execute action
- `/state` - Get current state
- `/tasks` - List all tasks
- `/ws` - WebSocket for real-time interaction

### Run Quick Test
Simple environment verification (no API key needed)
```bash
python main.py test
```

**Runs:**
1. CLASSIFY task (8% score)
2. ROUTE task (45% score)
3. RESOLVE task (28% score)

Takes ~5 seconds. Good for verify environment is working.

### Interactive Demo
Manual ticket interaction
```bash
python main.py demo
```

**Features:**
- Choose task (classify/route/resolve)
- Pick ticket (seed 0-29)
- Enter your answer manually
- See instant feedback and score

## Examples

### Quick verification (no setup needed)
```bash
python main.py test
```

### Full baseline with Groq
```bash
$env:GROQ_API_KEY='gsk_your_key_here'
python main.py baseline
```

### Launch production server
```bash
$env:GROQ_API_KEY='gsk_your_key_here'
python main.py server
# Open: http://localhost:8000/docs
```

### Try it manually
```bash
python main.py demo
# Choose task → Pick seed → Enter answer
```

## What Each Command Does

| Command | Purpose | Time | API Key? |
|---------|---------|------|----------|
| `main.py` | Show menu | 1s | No |
| `main.py test` | Quick verify | 5s | No |
| `main.py baseline` | Full evaluation | ~30min | **Yes** |
| `main.py server` | Start API | ∞ | **Yes** |
| `main.py demo` | Interactive | ∞ | No |

## Full Baseline Output

```
CLASSIFY (temperature=0.1):
  Mean: 68.0% (mostly deterministic)
  Range: 24.0% → 100.0%

ROUTE (temperature=0.5):
  Mean: 62.5% (some variation)
  Range: 15.0% → 100.0%

RESOLVE (temperature=0.7):
  Mean: 31.6% (high variation)
  Range: 19.0% → 51.0%

✅ DIFFICULTY GRADIENT: EASY (68%) > MEDIUM (62.5%) > HARD (31.6%)
```

## Architecture

```
main.py (single entry point)
  ├─ run_baseline()      → Full evaluation with Groq
  ├─ run_server()        → FastAPI server (REST + WebSocket)
  ├─ run_quick_test()    → 3-task verification
  ├─ run_interactive_demo()  → Manual ticket interaction
  └─ show_menu()         → Help information

Environment (customer_support_env/)
  ├─ environment.py      → Reward calculation + grading
  ├─ models.py           → Data structures
  ├─ data.py             → 30 support tickets
  └─ server/
      └─ app.py          → FastAPI endpoints
```

## File Dependencies

- **main.py** ← Entry point (import everything)
- **customer_support_env/** ← Core environment
- **requirements.txt** ← Dependencies

## Troubleshooting

### "GROQ_API_KEY not set"
```powershell
# Set it:
$env:GROQ_API_KEY='gsk_your_key'

# Verify:
$env:GROQ_API_KEY
```

### "groq package not installed"
```bash
pip install groq
```

### "uvicorn not installed" (when starting server)
```bash
pip install uvicorn
```

### "Import error"
Make sure you're running from the Hackathon directory:
```bash
cd d:\Hackathon
python main.py test
```

## Next Steps

1. **Quick verify:** `python main.py test`
2. **Set API key:** `$env:GROQ_API_KEY='gsk_...'`
3. **Run baseline:** `python main.py baseline`
4. **Start server:** `python main.py server`
5. **Deploy:** See DEPLOYMENT.md for HuggingFace Spaces

---

**Status:** ✅ Environment fully integrated, single entry point ready for production
