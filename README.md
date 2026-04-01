# 📖 Customer Support RL Environment - Complete Setup & Deployment Guide

**Project:** Customer Support RL Environment with Auto Agent & CI/CD Pipeline  
**Last Updated:** March 30, 2026  
**Status:** ✅ Ready to Deploy

---

## 📑 Table of Contents

1. [Verification & Testing Results](#verification--testing-results) ⭐ **START HERE - VERIFIED 3/30/26**
2. [Quick Start (5 Min)](#quick-start)
3. [Inference Script & Baseline](#inference-script--baseline-evaluation) ⭐ **NEW: Complete baseline guide**
4. [Architecture Overview](#architecture)
5. [Auto Agent Feature](#auto-agent)
6. [Streamlit UI Guide](#streamlit-ui)
7. [CI/CD Pipeline](#cicd-pipeline)
8. [Hugging Face Spaces Deployment](#hf-spaces)
9. [GitHub Actions Workflows](#github-actions)
10. [Benchmark & Reports](#benchmarks)
11. [Environment Setup](#environment)
12. [Troubleshooting](#troubleshooting)
13. [Deployment Checklist](#checklist)
14. [Documentation Files](#docs)

---

## 📚 Documentation Files

Complete documentation for this environment:

- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Quick deployment guide (choose this if you have 10 minutes)
- **[SPEC_COMPLIANCE.md](SPEC_COMPLIANCE.md)** — Detailed OpenEnv spec compliance checklist
- **[inference.py](inference.py)** — Official baseline agent (450 lines, heavily documented)
- **[README.md](README.md)** — This file (complete guide)

---

## 📑 Table of Contents

---

## 🧪 Verification & Testing Results

### ✅ Integration Tests (PASSED)
All environment components verified working:
```
✓ CLASSIFY task: reward=1.000
✓ ROUTE task: reward=1.000  
✓ RESOLVE task: reward=0.700 (correct: partial credit for complex scenario)
✓ Reward penalization works correctly
✓ Seeding reproducibility verified
✓ All 30 seeds (0-29) produce valid tickets
✓ Invalid inputs properly rejected
✓ Task-specific validation works

Results: 8 passed, 0 failed ✅
Your environment is ready for deployment.
```

### 📊 Baseline Evaluation Results ✅ (Verified 2026-03-30)

**Official Baseline Scores (Groq llama-3.3-70b-versatile, temperature=0.1):**
```
Classify (EASY):   86.2% (±21.8% std)  [30/30 episodes]
Route (MEDIUM):    76.3% (±20.0% std)  [30/30 episodes]
Resolve (HARD):    66.1% (±14.9% std)  [30/30 episodes]
─────────────────────────────────────
Overall Mean:      76.2%
```

**Raw Data:**
- Classify: min=0.24, max=1.0, mean=0.862, std=0.218
- Route: min=0.25, max=1.0, mean=0.763, std=0.2
- Resolve: min=0.29, max=0.913, mean=0.661, std=0.149

**How to Reproduce:**
```bash
# Set your Groq API key (free at https://console.groq.com)
$env:GROQ_API_KEY = "gsk_your_key_here"

# Run official benchmark (all 90 episodes, ~3 min)
python run_official_benchmark.py

# Scores are deterministic—run again to verify reproducibility
```

**Why These Scores?**
- **86.2% Classify:** Easy task—Groq excels at straightforward categorization
- **76.3% Route:** Medium task—some routing mistakes when departments are ambiguous
- **66.1% Resolve:** Hard task—LLM struggles with realistic response generation (longer text, more edge cases)
- **Meaningful variance:** 0.24 → 1.0 range shows the environment provides meaningful learning signal ✅

### 🐳 Docker Deployment Status
✅ **LIVE:** https://kavyabumiya-customer-support-env.hf.space
- Production Dockerfile validated ✅
- Health checks enabled ✅
- All endpoints operational ✅
- FastAPI /docs available at: https://kavyabumiya-customer-support-env.hf.space/docs

To test locally (requires Docker daemon):
```bash
docker build -t customer-support-env .
docker run -p 8000:8000 customer-support-env &
sleep 3
curl http://localhost:8000/health  # {"status": "healthy"}
```

---

## 📋 Quick Setup: Groq API Key Configuration

### ✅ API Key Already Configured (`.env` file)

Your environment is **pre-configured** for Groq:

```bash
# .env file contains:
GROQ_API_KEY=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
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
```

### OpenEnv Specification

Complete OpenEnv spec defined in [openenv.yaml](openenv.yaml):
- **API Version:** openenv_0.1
- **3 Tasks:** classify (easy), route (medium), resolve (hard)
- **Episode Type:** single-turn (one action → done)
- **Observation Fields:** 11 fields including reward and done signal
- **Task Schemas:** Typed action/observation models

See [openenv.yaml](openenv.yaml) for complete specification.

The `.env` file is **automatically loaded** by all Python scripts:
- `python run_official_benchmark.py` ✅
- `streamlit run streamlit_app.py` ✅  
- `python main.py baseline` ✅
- FastAPI server ✅

**No additional setup needed!** Just run the commands below.

---

## Quick Start

### 5-Minute Setup

#### Step 1: Push Code to GitHub
```bash
cd d:\Hackathon
git add .
git commit -m "feat: add CI/CD pipeline with Auto Agent and HF Spaces deployment"
git push origin main
```

#### Step 2: Add GitHub Secrets
Go to **GitHub Repository → Settings → Secrets and variables → Actions**

Add these 2 required secrets:

**Secret 1: GROQ_API_KEY**
- Get from: https://console.groq.com/keys
- Example: `gsk_xxxxxxxxxxxxxxxxxxxxx`

**Secret 2: HF_TOKEN**
- Get from: https://huggingface.co/settings/tokens
- Make sure to select **"Write" or "Admin"** permissions
- Example: `hf_xxxxxxxxxxxxxxxxxxxxx`

**Optional Secret: SLACK_WEBHOOK_URL** (for notifications)
- Get from: https://api.slack.com/messaging/webhooks

#### Step 3: Watch It Deploy
- Open GitHub Actions tab
- Monitor workflows (5-20 min total)
- Access app at: `https://huggingface.co/spaces/YOUR_USERNAME/customer-support-env`

#### Step 4: Test the App
1. Open deployed app URL
2. Go to "Interactive Demo"
3. Select "resolve" task
4. Click "Load New Ticket"
5. Click "🤖 Auto Agent" button
6. Review AI-generated response
7. Click "💾 Accept & Submit Auto"

**Done! App is live! 🚀**

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Repository                        │
└─────────────────────────────────────────────────────────────┘
         ↓ (git push)
┌─────────────────────────────────────────────────────────────┐
│              GitHub Actions Workflows                       │
├─────────────────────────────────────────────────────────────┤
│  ✅ Benchmark.yml         → Run LLM on 30 tickets          │
│  ✅ Deploy-hf-spaces.yml  → Build & deploy Docker          │
└─────────────────────────────────────────────────────────────┘
    ↓                               ↓
┌──────────────────────┐  ┌────────────────────────────────┐
│ JSON Reports         │  │ Hugging Face Spaces            │
│ (Benchmark Results)  │  │ (Live Streamlit App)           │
│                      │  │                                │
│ Reports stored:      │  │ URL:                           │
│ - GitHub Artifacts   │  │ https://huggingface.co/spaces/ │
│ - 30 day retention   │  │ YOUR_USERNAME/customer-...     │
└──────────────────────┘  └────────────────────────────────┘
```

### Workflow Triggers

| Event | Workflow | Action |
|-------|----------|--------|
| Push to `main` | Benchmark + Deploy | Run tests + deploy to HF Spaces |
| Push to `develop` | Benchmark only | Run tests only |
| Pull Request | Benchmark | Run tests, comment results |
| Daily midnight UTC | Benchmark | Scheduled automated run |
| Manual | Either | GitHub Actions UI trigger |

---

## Auto Agent Feature

### What It Does

The Streamlit app now includes a 🤖 **Auto Agent** button that:
1. Reads the current support ticket
2. Calls Groq LLM API with optimized prompt
3. Generates structured JSON response
4. Returns category, priority, department, and (for hard tasks) a customer response

### How It Works

#### Temperature Strategy
```
Task         Temperature    Behavior
────────────────────────────────────
Classify     0.1 (low)      Deterministic categorization
Route        0.5 (medium)   Some variation in routing
Resolve      0.7 (high)     Creative response generation
```

#### Generated Output Example

**Input Ticket:**
```
Subject: My billing shows duplicate charges
Body: I was charged twice for my subscription...
Customer Tier: premium
Sentiment: angry
```

**Auto Agent Output:**
```json
{
  "category": "billing",
  "priority": "high",
  "department": "billing",
  "requires_escalation": true,
  "response": "Dear valued customer, Thank you for bringing this to our attention. I sincerely apologize for the duplicate charges. I've reviewed your account and found the issue. Here's what I'm doing..."
}
```

### Using Auto Agent in Streamlit

#### Step 1: Set API Key
```powershell
$env:GROQ_API_KEY = "your-groq-api-key-here"
```

#### Step 2: Run Streamlit
```bash
streamlit run streamlit_app.py
```

#### Step 3: Use Auto Agent
1. Select task (classify/route/resolve)
2. Click "Load New Ticket"
3. Click "🤖 Auto Agent" button
4. Wait 2-5 seconds (LLM processing)
5. Review generated action
6. Click "💾 Accept & Submit Auto" or "❌ Reject Auto"

### Auto Agent Integration

**Modified File:** `streamlit_app.py`

**Features:**
- ✅ Robust error handling (missing API key, network errors)
- ✅ JSON parsing with fallback strategies
- ✅ Task-aware temperature settings
- ✅ Full integration with episode tracking
- ✅ Appears in Statistics tab same as manual actions

**UI Elements:**
- 🤖 Auto Agent button (generates response)
- 💾 Accept & Submit Auto (save generated response)
- ❌ Reject Auto (dismiss and try again)
- 🗑️ Clear Auto (clear without submitting)

---

## Streamlit UI Guide

### Interactive Demo Tab

#### Load Ticket
```
[🔄 Load New Ticket] [📌 Load Specific Ticket (seed)] [🗑️ Clear History]
```
- Click to get random or specific ticket
- Large dataset of 30 real support tickets

#### Ticket Information
```
📋 Ticket Details (expandable)
├─ Ticket ID: TSK-001
├─ Customer Tier: premium
├─ Previous Tickets: 2
├─ Open Since: 3 hours
├─ Sentiment: frustrated
├─ Subject: ...
└─ Body: ...
```

#### Action Input
```
Select Task:
├─ Classify (Easy) - Category + Priority
├─ Route (Medium) - + Department + Escalation
└─ Resolve (Hard) - + Customer Response

Fill in fields:
├─ Category: [billing/technical/account/general/shipping]
├─ Priority: [low/medium/high/urgent]
├─ Department: [tier1/tier2/billing/engineering/management]
├─ Requires Escalation: [checkbox]
└─ Response (resolve only): [text area]
```

#### Action Buttons (4 Options)
```
[✅ Submit Action] [🤖 Auto Agent] [⏭️ Skip] [🗑️ Clear Auto]
```

#### Auto-Generated Action Display
```
✅ Auto Agent Generated Action:

Category: billing        Priority: high
Department: billing     Escalation: ⚠️ Yes
Response: [Full generated text]

[💾 Accept & Submit Auto] [❌ Reject Auto]
```

#### Result Display
```
Score: 75%    Category: Billing    Priority: High    Department: Billing

💭 Feedback:
- Correct category classification ✓
- Priority well-assessed ✓
- Appropriate escalation decision ✓
```

### Statistics Tab

#### Summary Metrics
```
Total Episodes: 15
Average Reward: 72.5%
Best Score: 100%
Worst Score: 45%
```

#### Per-Task Breakdown
```
CLASSIFY  |  Episodes: 5  |  Avg: 78%  |  Best: 100%  |  Worst: 60%
ROUTE     |  Episodes: 5  |  Avg: 72%  |  Best: 95%   |  Worst: 50%
RESOLVE   |  Episodes: 5  |  Avg: 67%  |  Best: 85%   |  Worst: 45%
```

#### Reward Trend Chart
- Line graph showing reward over episodes
- Average line overlay
- Improvement metric tracking

#### Export Options
```
[📥 Download as CSV] [📥 Download as JSON]
```

### Batch Testing Tab

#### Configuration
```
Task: [classify/route/resolve]
Episodes: [1-100]
Strategy: [random/mean_values/all_high]
```

#### Automated Testing
- Runs multiple episodes automatically
- Random or template-based actions
- Bulk scoring
- Progress bar visualization

### Settings Tab

- Model selection
- Temperature adjustment (for advanced users)
- Batch size configuration
- Export/import history

---

## CI/CD Pipeline

### Overview

Automated testing and deployment pipeline:

| Component | Purpose | Trigger |
|-----------|---------|---------|
| **Benchmark** | Run 90 LLM evals (30 per task) | Push, PR, daily, manual |
| **Deploy** | Build Docker + deploy to HF | Push to main, manual |
| **Report** | Generate JSON benchmark results | Each benchmark run |
| **Notify** | Send Slack alerts | Workflow complete |

### Workflow Files

#### `.github/workflows/benchmark.yml`
```yaml
Triggers:
  - push: [main, develop]
  - pull_request: [main]
  - schedule: [daily at midnight UTC]
  - workflow_dispatch: [manual trigger]

Steps:
  1. Setup Python 3.11
  2. Install dependencies
  3. Run official benchmark
  4. Generate JSON reports
  5. Upload artifacts
  6. Comment on PR (if applicable)
  7. Notify Slack (if configured)

Duration: 3-5 minutes
```

#### `.github/workflows/deploy-hf-spaces.yml`
```yaml
Triggers:
  - push: [main only]
  - workflow_dispatch: [manual trigger]

Steps:
  1. Verify HF_TOKEN
  2. Push to HF Spaces (git push)
  3. Wait for HF build
  4. Health check deployed app
  5. Create GitHub deployment
  6. Notify Slack (if configured)

Duration: 5-15 minutes
```

### Configuration Files

#### `space_config.json` (HF Spaces Config)
```json
{
  "title": "Customer Support RL Environment - Auto Agent",
  "emoji": "🎫",
  "sdk": "docker",
  "app_port": 8501,
  "license": "mit"
}
```

#### `Dockerfile.streamlit` (Container Spec)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", ...]
```

#### `.env.example` (Environment Template)
```bash
# Groq API
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Temperature Settings
TEMPERATURE_CLASSIFY=0.1
TEMPERATURE_ROUTE=0.5
TEMPERATURE_RESOLVE=0.7

# Streamlit
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Benchmark
BENCHMARK_NUM_EPISODES=30
```

### Report Generation

#### `generate_benchmark_report.py`
Script that:
- Runs official benchmark
- Generates detailed JSON reports
- Creates summary statistics
- GitHub Actions compatible output
- Comparison functionality

**Usage:**
```bash
# Generate report
python generate_benchmark_report.py --output reports --mode official

# With GitHub Actions output
python generate_benchmark_report.py --output reports --github-actions

# Compare with previous
python generate_benchmark_report.py --output reports --compare-to previous.json
```

**Output Files:**
```
reports/
├─ report_official_20260330_120000.json  (detailed)
├─ report_summary_official.json          (quick lookup)
└─ benchmark_output.log                  (execution logs)
```

---

## Hugging Face Spaces Deployment

### Account Setup

1. **Create HF Account**
   - Go to https://huggingface.co
   - Sign up free
   - Create API token (write access)

2. **Create Space**
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Choose Docker SDK
   - Link GitHub repo or upload files

3. **Configure Space**
   - Settings → Secrets → Add `GROQ_API_KEY`
   - Settings → Secrets → Add other env vars (optional)

### File Structure for HF Spaces

```
repository/
├── Dockerfile.streamlit          ← Main Dockerfile (HF uses this)
├── space_config.json             ← HF Spaces metadata
├── streamlit_app.py              ← Main app (entry point)
├── requirements.txt              ← Python dependencies
├── customer_support_env/
│   ├── environment.py
│   ├── baseline.py
│   ├── data.py
│   ├── models.py
│   └── server/
└── README.md
```

### Deployment Process

```
Step 1: GitHub Action Detects Push
   ↓
Step 2: Checkout Code
   ↓
Step 3: Authenticate with HF (HF_TOKEN)
   ↓
Step 4: Push Repo to HF Spaces
   ↓
Step 5: HF Builds Docker Image (5-10 min)
   ↓
Step 6: Container Starts on Port 8501
   ↓
Step 7: Health Check Passes
   ↓
Step 8: 🎉 App Live!
   ↓
URL: https://huggingface.co/spaces/YOUR_USERNAME/customer-support-env
```

### Performance & Costs

| Item | Free Tier | Cost |
|------|-----------|------|
| Concurrent users | 1 | $0 |
| Storage | Unlimited | $0 |
| Bandwidth | Unlimited | $0 |
| Monthly cost | — | **$0** |
| Upgrade (5+ users) | Pro tier | $8/mo |

### Local Testing

Run Streamlit locally before deploying:

```bash
# 1. Set API key
$env:GROQ_API_KEY = "your-key"
$env:PYTHONIOENCODING = "utf-8"

# 2. Run app
streamlit run streamlit_app.py

# 3. Access at http://localhost:8501
```

### Docker Build Locally

```bash
# Build
docker build -f Dockerfile.streamlit -t customer-support:latest .

# Run
docker run -e GROQ_API_KEY="your-key" \
           -e PYTHONIOENCODING=utf-8 \
           -p 8501:8501 \
           customer-support:latest

# Access at http://localhost:8501
```

### Troubleshooting HF Spaces

| Issue | Solution |
|-------|----------|
| "OAuth token not set" | Set HF_TOKEN in GitHub Secrets |
| "Port 8501 not accessible" | Check `app_port: 8501` in space_config.json |
| "GROQ_API_KEY not found" | Add to HF Space Settings → Secrets |
| "Docker build failed" | Check requirements.txt, ensure Python 3.11 available |
| "App crashed" | Check HF Spaces logs (Settings → Logs) |
| "Can't reach URL" | Wait 2-3 min for warmup, refresh browser |

---

## GitHub Actions Workflows

### Manual Triggers

#### Run Benchmarks Now
1. Go to GitHub → **Actions**
2. Click **"Run Benchmarks"** workflow
3. Click **"Run workflow"** button
4. Select mode: `official` or `training`
5. Wait 3-5 minutes

#### Deploy Now
1. Go to GitHub → **Actions**
2. Click **"Deploy to Hugging Face Spaces"** workflow
3. Click **"Run workflow"** button
4. Wait 5-15 minutes

#### View Results
```
Actions → [Workflow] → [Run] → 
  - Logs (real-time output)
  - Artifacts (download reports)
  - Status (pass/fail)
```

### GitHub Status Checks

Branch protection rules can require passing tests:

```
Settings → Branch protection rules → Require status checks
├─ Run Benchmarks (required)
└─ Tests must pass before merge
```

### Slack Notifications

Optional: Get alerts on success/failure

Set `SLACK_WEBHOOK_URL` GitHub Secret:

```
✅ Deployment successful
Environment: HF Spaces
URL: https://huggingface.co/spaces/...

❌ Benchmark failed
Check GitHub Actions logs
```

---

## Benchmarks & Reports

### Official Benchmark

**File:** `run_official_benchmark.py` (existing)

**Runs:**
- 30 episodes per task (classify/route/resolve)
- Temperature: 0.1 (deterministic)
- Model: llama-3.3-70b-versatile (Groq)

**Command:**
```bash
$env:GROQ_API_KEY = "your-key"
$env:PYTHONIOENCODING = "utf-8"
python run_official_benchmark.py
```

**Output:**
```
OFFICIAL BENCHMARK (REPRODUCIBLE)

Running classify baseline on task: classify
Temperature: 0.1
Episode 0: score=0.950
Episode 1: score=0.450
...

Results for classify:
  Mean: 0.750
  Min:  0.300
  Max:  1.000
  Std:  0.150

Results for route:
  Mean: 0.650
  ...

Results for resolve:
  Mean: 0.550
  ...

OVERALL BASELINE RESULTS
Mean score: 0.650
Min score:  0.300
Max score:  1.000
```

### Training Baseline

**Mode:** Training with variable temperatures

```bash
python main.py baseline --mode training
```

**Temperatures:**
- Classify: 0.1 (low)
- Route: 0.5 (medium)
- Resolve: 0.7 (high)

**Use case:** Exploratory testing, model development

### Report Generated Format

**report_official_20260330_120000.json:**
```json
{
  "generated_at": "2026-03-30T12:00:00",
  "mode": "official",
  "model": "llama-3.3-70b-versatile",
  "episodes_per_task": 30,
  "temperature_strategy": {
    "classify": 0.1,
    "route": 0.1,
    "resolve": 0.1
  },
  "overall": {
    "mean": 0.65,
    "min": 0.2,
    "max": 1.0
  },
  "tasks": {
    "classify": {
      "mean": 0.75,
      "min": 0.3,
      "max": 1.0,
      "std": 0.15,
      "scores": [0.95, 0.45, 0.80, ...]
    },
    "route": {
      "mean": 0.65,
      ...
    },
    "resolve": {
      "mean": 0.55,
      ...
    }
  }
}
```

---

## Environment Setup

### 🟢 Groq API Configuration (Pre-Configured)

**The environment is already configured for Groq!** Your `.env` file contains:

```env
# .env (auto-loaded by all Python scripts)
GROQ_API_KEY=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
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile

# Temperature settings (per-task configuration)
GROQ_CLASSIFY_TEMP=0.1      # Deterministic
GROQ_ROUTE_TEMP=0.5         # Moderate variation
GROQ_RESOLVE_TEMP=0.7       # Creative responses
```

**How it works:**
1. Every Python script (`baseline.py`, `streamlit_app.py`, `main.py`, etc.) automatically loads the `.env` file
2. Environment variables are read by all LLM components
3. **No manual API key setup needed!** Just run the scripts.

**Verification:**
```bash
# Test that API key is loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key: ' + os.getenv('GROQ_API_KEY')[:30] + '...')"
```

---

### Local Development

#### 1. Python Environment

```bash
# Create venv
python -m venv .venv

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# Or activate (bash)
source .venv/bin/activate
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Key packages:**
- `groq>=0.4.0` — **Groq LLM API client** ⭐
- `streamlit>=1.28.0` — UI framework
- `fastapi>=0.104.0` — Server framework  
- `python-dotenv>=1.0.0` — `.env` file loading
- `pydantic>=2.0.0` — Data validation
- `pandas>=2.0.0` — Data handling
- `matplotlib>=3.7.0` — Visualization

#### 3. Verify .env File Exists

```bash
# Check .env file
ls -la .env

# Should contain GROQ_API_KEY=gsk_...
cat .env
```

**Windows (PowerShell):**
```powershell
Test-Path .env  # Should return True
Get-Content .env
```

#### 4. Run Baseline (Tests Groq Integration)

```bash
# Automatically loads GROQ_API_KEY from .env
python run_official_benchmark.py
```

Expected output:
```
✓ TICKETS validation passed: 30 tickets OK
============================================================
BASELINE EVALUATION: OFFICIAL BENCHMARK (temperature=0.1 all tasks)
============================================================
Running official baseline on task: classify
...
```

#### 5. Run Streamlit UI

```bash
streamlit run streamlit_app.py
```

Access at: http://localhost:8501

**The Auto Agent button will work automatically** (uses GROQ_API_KEY from `.env`)

#### 6. Start FastAPI Server

```bash
python main.py server
# Or directly:
uvicorn customer_support_env.server.app:app --reload
```

Access at: http://localhost:8000/docs

---

### GitHub Secrets (For CI/CD)

Go to **Settings → Secrets and variables → Actions**

Add these secrets for automated workflows:

| Secret | Purpose | Value |
|--------|---------|-------|
| `GROQ_API_KEY` | LLM API authentication | `gsk_...` |
| `HF_TOKEN` | HuggingFace Spaces deployment | `hf_...` (write access) |
| `SLACK_WEBHOOK_URL` | Slack notifications (optional) | Webhook URL from Slack API |

**How GitHub Actions uses them:**
```yaml
# .github/workflows/benchmark.yml
env:
  GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}

# Runs baseline automatically on push/PR
```

---

### Docker Deployment (HF Spaces)

The `Dockerfile.streamlit` is configured for Groq:

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code and .env
COPY . .

# Expose ports
EXPOSE 8501 8000

# Environment variables passed at runtime from HF Secrets
# Start Streamlit with GROQ_API_KEY from HF Spaces Settings
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0"]
```

**To deploy:**
1. Set `GROQ_API_KEY` in HF Space Settings → Secrets
2. Push code to GitHub
3. CI/CD automatically builds and deploys to HF Spaces
4. App runs with Groq API integration ✅

---

### Environment Variables Reference

| Variable | Default | Purpose | Required |
|----------|---------|---------|----------|
| `GROQ_API_KEY` | (from .env) | Groq API authentication | ✅ YES |
| `LLM_PROVIDER` | `groq` | LLM provider selection | Optional |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Model to use | Optional |
| `GROQ_CLASSIFY_TEMP` | `0.1` | Temperature for classify task | Optional |
| `GROQ_ROUTE_TEMP` | `0.5` | Temperature for route task | Optional |
| `GROQ_RESOLVE_TEMP` | `0.7` | Temperature for resolve task | Optional |
| `PYTHONIOENCODING` | `utf-8` | Terminal encoding (Windows) | Optional |
| `BENCHMARK_EPISODES_PER_TASK` | `30` | Episodes per task | Optional |
| `BENCHMARK_TEMPERATURE` | `0.1` | Benchmark temp (official mode) | Optional |

---

### Getting Your Own Groq API Key

If you want to replace the API key:

1. **Go to:** https://console.groq.com/keys
2. **Create API key** → Copy to clipboard
3. **Update `.env` file:**
   ```env
   GROQ_API_KEY=gsk_your_new_key_here
   ```
4. **Or set environment variable:**
   ```bash
   $env:GROQ_API_KEY = "gsk_..."
   ```

**Free Tier:**
- 100 requests/minute (more than sufficient)
- Unlimited models: llama-3.3-70b, mixtral-8x7b, etc.
- $0 cost

---

### Troubleshooting Environment Setup

| Issue | Solution |
|-------|----------|
| "GROQ_API_KEY environment variable not set" | Create `.env` file with `GROQ_API_KEY=gsk_...` or run `python -m dotenv set GROQ_API_KEY gsk_...` |
| "groq package not installed" | Run `pip install groq` or `pip install -r requirements.txt` |
| "UnicodeEncodeError" on Windows | Set `$env:PYTHONIOENCODING = "utf-8"` before running |
| ".env file not loading" | Ensure `.env` is in project root directory, run `from dotenv import load_dotenv; load_dotenv()` in Python |
| "Connection timeout" | Check internet connection, Groq API status at https://status.groq.com |
| "Invalid API key" | Verify key starts with `gsk_`, copy exactly (no spaces/quotes) |

---

### GitHub Secrets

Go to **Settings → Secrets and variables → Actions**

| Secret | Purpose |
|--------|---------|
| `HF_TOKEN` | HF Spaces deployment |
| `SLACK_WEBHOOK_URL` | Notifications (optional) |

### HF Spaces Secrets

Go to **Space Settings → Secrets**

Same secrets as GitHub:
- `GROQ_API_KEY`
- `SLACK_WEBHOOK_URL` (optional)

---

## Troubleshooting

### Common Issues

#### Benchmarks Won't Run

**Error:** "GROQ_API_KEY environment variable not set"

**Solution:**
1. Go to GitHub Settings → Secrets
2. Click "New repository secret"
3. Name: `GROQ_API_KEY`
4. Value: Your Groq API key
5. Click "Add secret"
6. Push code again to trigger workflow

#### Deployment Fails

**Error:** "HF_TOKEN not set" or "Permission denied"

**Solution:**
1. Get new HF token: https://huggingface.co/settings/tokens
2. Ensure token has **Write** permissions
3. Go to GitHub Settings → Secrets
4. Update `HF_TOKEN`
5. Manually trigger deploy workflow

#### Unicode Encoding Error

**Error:** "UnicodeEncodeError: 'charmap' codec can't encode"

**Solution:**
```powershell
# Set encoding before running Python
$env:PYTHONIOENCODING = "utf-8"
python run_official_benchmark.py
```

#### Port Already in Use

**Error:** "Error binding to :: port 8501"

**Solution:**
```bash
# Use different port
streamlit run streamlit_app.py --server.port 8502
```

#### Module Not Found

**Error:** "ModuleNotFoundError: No module named 'groq'"

**Solution:**
```bash
pip install -r requirements.txt
# Or specific package:
pip install groq
```

#### App Won't Start on HF Spaces

**Error:** Container crashed or won't respond

**Solution:**
1. Check HF Spaces logs (Space Settings → Logs)
2. Verify `GROQ_API_KEY` is set in Space Secrets
3. Check `app_port: 8501` in space_config.json
4. Wait 2-3 min for container warmup
5. Refresh browser

#### Streamlit Auto Agent Not Working

**Error:** "GROQ_API_KEY not set" in Streamlit

**Solution:**
```powershell
# Set before running Streamlit
$env:GROQ_API_KEY = "your-key"
streamlit run streamlit_app.py
```

#### PR Comment Not Appearing

**Issue:** Benchmark runs but no comment on PR

**Causes:**
- Workflow failed (check logs)
- GitHub actions token lacks permissions
- Running on fork (GitHub Actions limitation)

**Solution:**
Check workflow logs for errors, manually trigger if needed

### Monitoring & Debugging

#### View Workflow Logs

```
GitHub → Actions → [Workflow] → [Run] → Logs
```

Real-time output, searchable, expandable per step

#### View App Logs

**HF Spaces:**
```
Space URL → Settings → Logs
```

**Local Docker:**
```bash
docker logs <container-id> --follow
```

---

## Inference Script & Baseline Evaluation

### Overview

The **`inference.py`** script is the official baseline agent for evaluating the Customer Support Environment. It demonstrates:

- ✅ **Spec Compliance:** Full OpenEnv spec implementation
- ✅ **Proper Logging:** Structured [START], [STEP], [END] format for evaluation
- ✅ **Reproducibility:** Deterministic scores across runs with fixed seeds
- ✅ **Real LLM Integration:** Uses OpenAI Client to query any OpenAI-compatible API
- ✅ **All 3 Tasks:** Classify (easy), Route (medium), Resolve (hard)
- ✅ **Efficient:** Completes in <5 minutes on modest hardware (vcpu=2, memory=8GB)

### Required Configuration

Before running inference, set three environment variables:

```powershell
# API endpoint (choose one)
$env:API_BASE_URL="https://router.huggingface.co/v1"          # Hugging Face
# $env:API_BASE_URL="https://api.groq.com/openai/v1"          # Groq
# $env:API_BASE_URL="http://localhost:11434/v1"               # Local Ollama

# Model identifier (must match your API endpoint)
$env:MODEL_NAME="meta-llama/Llama-2-7b-chat-hf"               # HF router
# $env:MODEL_NAME="llama-3.3-70b-versatile"                    # Groq
# $env:MODEL_NAME="llama2"                                     # Ollama

# API key / token (from your selected provider)
$env:HF_TOKEN="hf_your_token_here"                            # HF token
# $env:HF_TOKEN="gsk_your_groq_key_here"                       # Groq key
# $env:HF_TOKEN="sk_your_openai_key_here"                      # OpenAI key
```

### Setup Instructions

#### Step 1: Get API Credentials

Choose **one** of the following:

**Option A: Hugging Face API (Recommended)**
1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Create new token with **"Write"** permission
3. Copy token

**Option B: Groq API**
1. Go to [console.groq.com/keys](https://console.groq.com/keys)
2. Create new API key
3. Copy key

**Option C: Local Ollama**
1. Install Ollama: [ollama.ai](https://ollama.ai)
2. Start server: `ollama serve`
3. Pull model: `ollama pull llama2`
4. No API key needed (use any dummy value)

#### Step 2: Configure Environment

```bash
# Create .env file or edit existing one
# Copy .env.example as starting point:
cp .env.example .env

# Edit .env with your credentials:
#   API_BASE_URL=https://router.huggingface.co/v1
#   MODEL_NAME=meta-llama/Llama-2-7b-chat-hf
#   HF_TOKEN=hf_your_token_here
```

Or set via terminal (one-liner):

```powershell
$env:API_BASE_URL="https://router.huggingface.co/v1"; `
$env:MODEL_NAME="meta-llama/Llama-2-7b-chat-hf"; `
$env:HF_TOKEN="hf_your_token_here"
```

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `openai>=1.0.0` - OpenAI Client for flexible API access
- `fastapi` + `uvicorn` - Server framework
- `pydantic` - Data validation
- Other utilities

### Running Inference

#### Quick Start (3 episodes)

```bash
python inference.py
```

This runs:
- 1 episode per task (classify, route, resolve)
- Uses fixed seeds for reproducibility
- Outputs [START], [STEP], [END] logs to stdout
- Completes in ~30-60 seconds

Expected output:
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

#### Modify Number of Episodes

Edit `inference.py` and change `NUM_SEEDS`:

```python
NUM_SEEDS = 3   # Default: 3 seeds per task = 9 total episodes
NUM_SEEDS = 30  # Full benchmark: 30 seeds per task = 90 total episodes (~15 min)
```

### OpenAI Client Configuration

The script uses the OpenAI Python client but points to custom endpoints:

```python
from openai import OpenAI

client = OpenAI(
    api_key=API_KEY,                    # Your token
    base_url=API_BASE_URL               # Custom endpoint
)

response = client.chat.completions.create(
    model=MODEL_NAME,                   # Model identifier
    messages=[...],
    temperature=0.3,
    max_tokens=500
)
```

This approach supports:
- ✅ Hugging Face Inference API
- ✅ Groq API (grok.ai)
- ✅ Local Ollama
- ✅ Standard OpenAI
- ✅ Any OpenAI-compatible endpoint

### Understanding the Output Format

The script emits exactly 3 line types per episode:

**[START] Line:**
- Emitted once at episode begin
- Format: `[START] task=<name> env=<benchmark> model=<name>`
- Purpose: Marker for evaluation system to initialize

**[STEP] Lines:**
- Emitted once per environment step
- Format: `[STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>`
- Fields:
  - `step`: Integer step number
  - `action`: Human-readable action (JSON fields as key=value pairs)
  - `reward`: Floating point value, 2 decimal places
  - `done`: Lowercase boolean (true/false)
  - `error`: Error message or "null"

**[END] Line:**
- Emitted once at episode end (even on exception)
- Format: `[END] success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>`
- Fields:
  - `success`: Episode succeeded (score >= 0.1)
  - `steps`: Total steps taken
  - `score`: Final normalized score (0.0-1.0)
  - `rewards`: Comma-separated list, 2 decimal places

### Troubleshooting

#### Error: `HF_TOKEN not set`

```
[ERROR] HF_TOKEN / API_KEY not set in environment. Export it and retry.
```

**Fix:** Export the token before running:
```bash
export HF_TOKEN="hf_your_token_here"
python inference.py
```

#### Error: `openai package not installed`

```
[ERROR] openai package not installed. Install with: pip install openai
```

**Fix:**
```bash
pip install openai>=1.0.0
```

#### Error: Model not found or not available

```
LLM request error: The model `xyz` does not exist or you don't have access to it
```

**Fix:**
- Verify `MODEL_NAME` exists for your `API_BASE_URL`
- Check API token has correct permissions
- For HF: token needs "Read" or "Write" permission
- For Groq: model must be supported by Groq (check their docs)

#### Error: Timeout or slow responses

```
[ERROR] LLM request failed: Request timed out
```

**Fix:**
- The inference script waits 30 seconds per LLM call
- Retry with a simpler model or fewer episodes
- Check your internet connection
- Try local Ollama (no network required)

#### Episodes all failing with reward=0.0

This can happen if the LLM doesn't output valid JSON. Check:
1. Is the prompt reaching the LLM? (Look for "[DEBUG]" logs)
2. Is the LLM responding in English JSON format?
3. Try with a larger model (7B → 13B → 70B)

### Baseline Scores Reference

With Hugging Face router + Llama-2-7B model:

```
classify (EASY):    ~0.70 average score
route (MEDIUM):     ~0.55 average score
resolve (HARD):     ~0.45 average score
```

These scores vary with model selection and temperature. Your environment should produce meaningful variance in this range.

## Deployment Checklist

### Pre-Deployment

- [ ] All files created:
  - [ ] `space_config.json`
  - [ ] `Dockerfile.streamlit`
  - [ ] `.env.example`
  - [ ] `generate_benchmark_report.py`
  - [ ] `.github/workflows/benchmark.yml`
  - [ ] `.github/workflows/deploy-hf-spaces.yml`
  - [ ] `streamlit_app.py` (enhanced with Auto Agent)

- [ ] Local testing done:
  - [ ] Set `GROQ_API_KEY`
  - [ ] Run `streamlit run streamlit_app.py`
  - [ ] Test Auto Agent button
  - [ ] Verify Statistics tab works

### Deployment

- [ ] Push to GitHub:
  ```bash
  git push origin main
  ```

- [ ] Add GitHub Secrets:
  - [ ] `GROQ_API_KEY` from Groq console
  - [ ] `HF_TOKEN` from HF with write access
  - [ ] (Optional) `SLACK_WEBHOOK_URL`

- [ ] Monitor workflows:
  - [ ] GitHub Actions tab
  - [ ] Benchmarks running (3-5 min)
  - [ ] Deploy starting (5-15 min)

- [ ] Access deployed app:
  - [ ] HF Space URL loads
  - [ ] Streamlit UI responsive
  - [ ] Auto Agent button works

### Post-Deployment

- [ ] Test Auto Agent:
  - [ ] Load ticket
  - [ ] Click "🤖 Auto Agent"
  - [ ] Review response
  - [ ] Submit and score

- [ ] Check statistics:
  - [ ] Go to Statistics tab
  - [ ] Episodes tracked
  - [ ] Scores visible
  - [ ] Export works

- [ ] Monitor production:
  - [ ] Check HF Spaces logs weekly
  - [ ] Review benchmark reports
  - [ ] Track average scores

---

## Quick Reference

### Commands

```bash
# Local development
$env:GROQ_API_KEY = "your-key"
streamlit run streamlit_app.py    # Run app (http://localhost:8501)

# Benchmarking
$env:PYTHONIOENCODING = "utf-8"
python run_official_benchmark.py  # Run official benchmark

# Report generation
python generate_benchmark_report.py --output reports --mode official

# Docker
docker build -f Dockerfile.streamlit -t myapp:latest .
docker run -e GROQ_API_KEY=$KEY -p 8501:8501 myapp:latest
```

### URLs

```
GitHub Secrets:
https://github.com/YOUR_USERNAME/customer-support-env/settings/secrets/actions

GitHub Actions:
https://github.com/YOUR_USERNAME/customer-support-env/actions

HF Space:
https://huggingface.co/spaces/YOUR_USERNAME/customer-support-env

Groq Console:
https://console.groq.com/keys

HF Tokens:
https://huggingface.co/settings/tokens
```

### Key Credentials

Get from official sources:

| Credential | Source | Purpose |
|-----------|--------|---------|
| `GROQ_API_KEY` | https://console.groq.com/keys | LLM API calls |
| `HF_TOKEN` | https://huggingface.co/settings/tokens | HF Spaces deployment |
| `SLACK_WEBHOOK_URL` | https://api.slack.com/messaging/webhooks | Notifications (optional) |

---

## Support & Documentation

### Official Docs
- GitHub Actions: https://docs.github.com/en/actions
- HF Spaces: https://huggingface.co/docs/hub/spaces
- Groq API: https://console.groq.com/docs
- Streamlit: https://docs.streamlit.io
- Docker: https://docs.docker.com

### Model Information
- Model: `llama-3.3-70b-versatile` (Groq)
- Provider: Groq API
- Temperatures: 0.1 (classify), 0.5 (route), 0.7 (resolve)

### Dataset
- 30 support tickets
- Real-world scenarios
- Multiple categories, priorities, departments

---

## Success Criteria

✅ **You're Done When:**
- Code pushed to GitHub
- Workflows completed in Actions tab
- App accessible at HF Spaces
- Auto Agent button working
- Benchmark reports generated
- Statistics tracked

✅ **Everything Working When:**
1. Benchmarks run automatically on push
2. Reports generated within 5 minutes
3. Deployment completes within 15 minutes
4. App is live and responsive
5. Auto Agent generates responses
6. Scores tracked in Statistics tab
7. Can export data to CSV/JSON

---

## Next Steps (In Order)

1. **Push to GitHub** (5 min)
   ```bash
   git push origin main
   ```

2. **Add Secrets** (5 min)
   - Go to GitHub Settings → Secrets
   - Add `GROQ_API_KEY` and `HF_TOKEN`

3. **Monitor Workflows** (20 min)
   - Check Actions tab
   - Wait for benchmarks to complete
   - Wait for deployment to complete

4. **Test App** (5 min)
   - Open HF Spaces URL
   - Test Auto Agent button
   - Check Statistics tab

5. **Download Reports** (2 min)
   - Go to GitHub Actions
   - Download benchmark reports

6. **Share & Celebrate** 🎉
   - Your app is live!
   - Production-ready CI/CD pipeline
   - Automated benchmarking
   - Zero-cost deployment

---

## Final Notes

### Important Reminders

- 🔒 **Never commit API keys** — Always use GitHub Secrets
- 📝 **Keep `.env` local** — Use `.env.example` as template
- 🚀 **Deploy only from `main`** — Use `develop` for testing
- 📊 **Check reports regularly** — Monitor performance trends
- 🔔 **Set up Slack** (optional) — Get deployment alerts

### Cost Breakdown

| Item | Cost |
|------|------|
| GitHub Actions (free tier) | $0 |
| HF Spaces (free tier) | $0 |
| Groq API | $0 (free tier, some limits) |
| **Total Monthly** | **$0** ✅ |

### Timeline

| Event | Duration |
|-------|----------|
| Push code | 1 sec |
| Benchmark runs | 3-5 min |
| Deployment builds | 5-10 min |
| App goes live | 15-20 min total |
| Report available | Same as benchmark |

---

## Conclusion

You now have:
✅ Automated CI/CD pipeline  
✅ AI-powered Auto Agent for Streamlit  
✅ Benchmark automation  
✅ JSON performance reports  
✅ Zero-cost deployment to HF Spaces  
✅ Production-ready infrastructure  

**Ready to deploy? Follow the checklist above and push to GitHub! 🚀**

---

**Document Version:** 1.0  
**Last Updated:** March 30, 2026  
**Status:** ✅ Complete & Ready to Deploy
