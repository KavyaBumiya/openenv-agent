# Deployment Guide: Customer Support RL Environment

## Quick Start

### Local Development

```bash
# 1. Clone and install
git clone https://github.com/KavyaBumiya/openenv-agent.git
cd openenv-agent
pip install -r requirements.txt

# 2. Create .env file
cat > .env << EOF
API_BASE_URL=https://router.huggingface.co/v1
MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct
HF_TOKEN=your_huggingface_token_here
EOF

# 3. In terminal 1: Start the environment server
python -m uvicorn customer_support_env.server.app:app --port 7860 --reload

# 4. In terminal 2: Run the baseline agent
export HF_TOKEN="your_huggingface_token_here"
python inference.py

# 5. Output appears as
# [START] task=classify env=customer_support_env model=...
# [STEP] step=1 action={"category":"billing",...} reward=1.00 done=true error=null
# [END] success=true steps=1 rewards=1.00
```

---

## Docker Deployment (Local Testing)

```bash
# 1. Build image
docker build -t customer-support-env .

# 2. Run container
docker run \
  -p 7860:7860 \
  -e API_BASE_URL="https://router.huggingface.co/v1" \
  -e MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct" \
  -e HF_TOKEN="your_token" \
  customer-support-env

# 3. Test from another terminal
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "classify", "seed": 0}'
```

---

## Hugging Face Spaces Deployment

### Step 1: Create Space

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click "Create new Space"
3. Fill in:
   - **Space name**: `customer-support-env` (or similar)
   - **License**: MIT
   - **Space SDK**: Docker
   - **Private/Public**: Public recommended
4. Click "Create Space"

### Step 2: Push Repository

```bash
# Option A: Using Git
git clone https://huggingface.co/spaces/YOUR_USERNAME/customer-support-env
cd customer-support-env
cp -r /path/to/this/repo/* .
git add .
git commit -m "Initial commit: customer support environment"
git push

# Option B: Upload files directly via web UI
# Go to Space page → Files → Upload files
```

### Step 3: Set Secrets

Space → Settings → Secrets:

```
API_BASE_URL = https://router.huggingface.co/v1
MODEL_NAME = meta-llama/Llama-3.1-8B-Instruct
HF_TOKEN = hf_xxxxxxxxxxxxxxxxxxxx  (your HF API token)
ENV_BASE_URL = (leave empty; Space URL will be used)
```

### Step 4: Verify Deployment

1. Wait for Docker build to complete (~5 minutes)
2. Once "Running" status shows, click "App" tab
3. Test the API:

```bash
curl -X POST https://YOUR_USERNAME-customer-support-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "classify", "seed": 0}'
```

Should return HTTP 200 with observation object.

---

## Pre-Submission Validation

### Run Validator Script

```bash
chmod +x scripts/validate-submission.sh
./scripts/validate-submission.sh https://YOUR_USERNAME-customer-support-env.hf.space .
```

This checks:
- ✓ Space /reset endpoint responds (HTTP 200)
- ✓ Docker build succeeds
- ✓ `openenv validate` passes

### Manual Checks

1. **Environment responds:**
   ```bash
   curl -s http://localhost:7860/health | jq
   # Expected: {"status": "healthy"}
   ```

2. **Full episode works:**
   ```bash
   export HF_TOKEN="your_token"
   python inference.py
   # Should produce 9 episodes (3 tasks × 3 seeds)
   ```

3. **OpenEnv spec valid:**
   ```bash
   pip install openenv-core
   openenv validate
   # Should pass
   ```

---

## Environment Variables Reference

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `API_BASE_URL` | Yes* | `https://router.huggingface.co/v1` | OpenAI-compatible endpoint |
| `MODEL_NAME` | Yes* | `meta-llama/Llama-3.1-8B-Instruct` | Model identifier |
| `HF_TOKEN` | Yes* | - | API key (for inference.py) |
| `ENV_BASE_URL` | No | `http://localhost:7860` | Server URL (for inference.py) |
| `BASELINE_OUTPUT_PATH` | No | `baseline_scores.json` | Output file for scores |
| `LOCAL_IMAGE_NAME` | No | - | Docker image name (compatibility) |

\* Required for inference.py; optional for server operation

---

## Troubleshooting

### Docker Build Fails
```bash
# Clear cache and rebuild
docker build -t customer-support-env --no-cache .
```

### Server Won't Start
```bash
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Try manual start
python -m uvicorn customer_support_env.server.app:app --port 7860
```

### API Returns 500 Error
```bash
# Check logs
docker logs <container_id>

# Or in local mode
# Look for stack trace in terminal
```

### Inference Script Hangs
```bash
# Increase timeout
ENV_BASE_URL="http://localhost:7860" timeout 120 python inference.py
```

### Out of Memory
The environment runs on ~512MB. If DockerSpace has OOM issues:
1. Reduce `MAX_SESSIONS` in `server/app.py` (currently 200)
2. Or use smaller model (e.g., `meta-llama/Llama-2-7b-chat-hf`)

---

## Performance Notes

- **Classify**: ~150ms per step
- **Route**: ~200ms per step
- **Resolve**: ~500ms per step (includes response generation)
- **Memory**: ~200MB idle, ~1GB during inference
- **Concurrency**: Supports 200 concurrent sessions

---

## Support & Citation

If this environment is used in published work, please cite:

```bibtex
@misc{customer_support_env,
  title={Customer Support RL Environment: Real-world LLM Agent Benchmark},
  author={Kavya B.},
  year={2026},
  url={https://huggingface.co/spaces/YOUR_USERNAME/customer-support-env}
}
```

For issues, please open a GitHub issue or contact the maintainer.

---

**Last Updated**: April 2026
