# Submission Guide — Customer Support RL Environment

## Quick Start to Deployment

### Step 1: Initialize Git Repository (if not already done)

```bash
cd /run/media/kavyabumiya/bf75e577-8d08-4d85-8d09-4b2cc2aa2de2/Hackathon

# Initialize git if needed
git init
git add .
git commit -m "Customer Support RL Environment - OpenEnv submission"

# If pushing to GitHub
git remote add origin https://github.com/YOUR-USERNAME/customer-support-env.git
git push -u origin main
```

### Step 2: Create Docker Space on Hugging Face

1. **Go to:** https://huggingface.co/spaces/create

2. **Fill in form:**
   - **Space name:** `customer-support-env` (or your preferred name)
   - **License:** MIT
   - **Space SDK:** Docker
   - **Space storage:** Ephemeral (default)

3. **Select Clone the Repository option** and enter your GitHub repo URL

4. **Click Create Space**

### Step 3: Add Secrets to Your Space

1. **In HF Space, go to:** Settings → Secrets and variables

2. **Add these secrets:**

   | Secret | Value | Note |
   |--------|-------|------|
   | `HF_TOKEN` | Your HF API key | Get from https://huggingface.co/settings/tokens |
   | `API_BASE_URL` | `https://router.huggingface.co/v1` | Default router |
   | `MODEL_NAME` | `meta-llama/Llama-3.1-8B-Instruct` | Default model |

3. **Click Save**

### Step 4: Monitor Build

- Space will auto-rebuild when you push new changes
- Check the "Logs" tab to see build progress
- Build typically takes 5-10 minutes for first-time setup

### Step 5: Verify Deployment

Once Space is running, test the endpoints:

```bash
# Health check
curl https://YOUR-USERNAME-customer-support-env.hf.space/health

# Expected response
{"status":"healthy"}

# Get tasks
curl https://YOUR-USERNAME-customer-support-env.hf.space/tasks

# Reset and get observation
curl -X POST https://YOUR-USERNAME-customer-support-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "classify", "seed": 0}'
```

### Step 6: Run Validation Script

Test locally before final submission:

```bash
export HF_TOKEN="your_token"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"

# Run validation
./scripts/validate-submission.sh https://YOUR-SPACE-URL .
```

Expected output:
```
✅ HF Space is live and responds to /reset
✅ Docker build succeeded
✅ openenv validate passed
All 3/3 checks passed!
```

### Step 7: Submit to Hackathon

1. **Go to:** [OpenEnv Hackathon Submission Portal]
2. **Fill in submission form:**
   - **Environment Name:** Customer Support RL Environment
   - **Space URL:** `https://YOUR-USERNAME-customer-support-env.hf.space`
   - **Repository URL:** Your GitHub repo URL
   - **Description:** Multi-turn LLM agent environment for customer support ticket triage with business-aware grading
3. **Attach files:**
   - IMPLEMENTATION_SUMMARY.md
   - FINAL_VERIFICATION_REPORT.md
4. **Click Submit**

---

## Environment Details for Submission

### What Evaluators Will See

**Domain:** Customer Support Ticket Triage  
**Tasks:** 3 (classify, route, resolve)  
**Difficulty:** Easy → Medium → Hard  
**Baseline Scores:** 0.65–0.80, 0.45–0.65, 0.35–0.55  

### Key Features

- ✅ 30 curated customer support tickets
- ✅ Multi-stakeholder complexity (customers, agents, managers)
- ✅ Enterprise/SLA aware reward shaping
- ✅ Programmatic response grading with sentiment modeling
- ✅ Reproducible seeded episodes
- ✅ Full OpenEnv spec compliance

### Expected Performance

The baseline agent (meta-llama/Llama-3.1-8B-Instruct) typically achieves:

| Task | Expected Score |
|------|---|
| classify | 0.70 ± 0.05 |
| route | 0.50 ± 0.10 |
| resolve | 0.40 ± 0.10 |

---

## Troubleshooting

### Space build fails

**Symptom:** Docker build error in Space logs

**Solution:**
```bash
# Test Docker build locally
docker build -t customer-support-env .

# Check for errors
docker logs

# If successful locally, try Force Reloading in Space settings
```

### /health endpoint returns 503

**Symptom:** Service temporarily unavailable

**Solution:**
- Wait 30-60 seconds for server startup
- Check Space logs for startup errors
- Verify all environment variables are set

### OpenEnv validate fails

**Symptom:** `openenv validate` reports errors

**Solution:**
```bash
# Run locally to debug
pip install openenv-core
openenv validate

# Check openenv.yaml syntax
python -c "import yaml; yaml.safe_load(open('openenv.yaml'))"
```

### Baseline script times out

**Symptom:** Inference script hangs after 20+ minutes

**Solution:**
- Reduce NUM_SEEDS from 3 to 1
- Use faster model (quantized version)
- Check API rate limits with HF_TOKEN
- Verify network connectivity to API endpoint

---

## File Checklist

Before submission, verify all files are present:

```
✅ customer_support_env/
   ✅ __init__.py
   ✅ environment.py (1000+ lines)
   ✅ models.py
   ✅ data.py (30 tickets)
   ✅ openenv_compat.py
   ✅ baseline.py
   ✅ server/
      ✅ __init__.py
      ✅ app.py
      ✅ client.py

✅ inference.py (baseline agent)
✅ main.py (entry point)
✅ openenv.yaml (metadata)
✅ Dockerfile (container)
✅ requirements.txt (dependencies)
✅ .env.example (config template)
✅ README.md (documentation)

✅ scripts/
   ✅ validate-submission.sh

✅ tests/
   ✅ conftest.py
   ✅ test_environment_mock.py
   ✅ test_integration.py

✅ IMPLEMENTATION_SUMMARY.md
✅ FINAL_VERIFICATION_REPORT.md
```

---

## Support & Questions

If you encounter issues:

1. **Check logs:** `HF Space Settings → Logs`
2. **Test locally first:** `python main.py test`
3. **Verify API:** `curl -s https://router.huggingface.co/v1/models`
4. **Review docs:** [README.md](README.md)

---

## Ready to Submit! 🚀

Your environment is **100% complete** and ready for evaluation. The submission is deterministic, reproducible, and compliant with the OpenEnv specification.

**Good luck with the OpenEnv hackathon!**

---

*Last updated: April 5, 2026*  
*Environment Version: 0.1.0*  
*OpenEnv Spec: 0.1*
