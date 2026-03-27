# Deployment Guide: HuggingFace Spaces

Deploy your Customer Support RL Environment to HuggingFace Spaces in 5 minutes.

## Prerequisites

1. **HuggingFace Account** - Free tier is fine (https://huggingface.co/join)
2. **Git & Git LFS** - For pushing large files
3. **Groq API Key** - Get free at https://console.groq.com

---

## Step 1: Create HuggingFace Space

1. Go to **https://huggingface.co/spaces**
2. Click **Create new Space**
3. Fill in:
   - **Space name**: `customer-support-env` (or your choice)
   - **License**: MIT
   - **Space SDK**: Docker
   - **Space hardware**: CPU basic (free tier)
4. Click **Create Space**

---

## Step 2: Clone the Space Repository

```bash
# Replace YOUR_USERNAME with your HuggingFace username
git clone https://huggingface.co/spaces/YOUR_USERNAME/customer-support-env
cd customer-support-env
```

---

## Step 3: Copy Your Code

Copy all files from your local repo:

```bash
# From your local Hackathon directory
cp -r d:\Hackathon\* ./                # On Windows use: xcopy

# Key files to include:
#   - customer_support_env/
#   - tests/
#   - Dockerfile
#   - requirements.txt
#   - README.md
```

---

## Step 4: Git Push to HuggingFace

```bash
git add .
git commit -m "Initial deployment: Customer Support RL Environment"
git push origin main
```

HuggingFace will automatically:
1. Detect `Dockerfile`
2. Build the Docker image
3. Deploy container on given hardware
4. Expose on `https://YOUR_USERNAME-customer-support-env.hf.space`

**Build takes ~3-5 minutes** ⏳

---

## Step 5: Set Environment Variables

Once deployed:

1. Go to your Space settings: **https://huggingface.co/spaces/YOUR_USERNAME/customer-support-env/settings**
2. Scroll to **Repository secrets**
3. Add secret:
   - **Name**: `GROQ_API_KEY`
   - **Value**: `gsk_...` (your Groq API key)
4. Click **Add secret**
5. **Restart the Space** (Settings → App startup section)

---

## Step 6: Test Your Deployment

Once running:

```bash
# View live logs (Settings → Logs tab in HuggingFace UI)

# Test endpoints
curl https://YOUR_USERNAME-customer-support-env.hf.space/tasks
curl https://YOUR_USERNAME-customer-support-env.hf.space/docs

# Test baseline
curl -X POST \
  https://YOUR_USERNAME-customer-support-env.hf.space/baseline \
  -H "Content-Type: application/json" \
  -d '{"num_episodes": 30}'
```

---

## Local Testing Before Deploy

Highly recommended!

```bash
# Build Docker locally
docker build -t customer-support-env .

# Run with environment variable
docker run -p 8000:8000 \
  -e GROQ_API_KEY="gsk_..." \
  customer-support-env

# Test at http://localhost:8000/docs
```

---

## API Endpoints Available

Once deployed, access:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/tasks` | GET | Task definitions |
| `/reset` | POST | Start episode |
| `/step` | POST | Take action |
| `/state` | GET | Current state |
| `/grader` | GET | Scoring philosophy |
| `/baseline` | POST | Run 30 episodes |
| `/docs` | GET | Interactive docs |

### Example Request

```bash
# List tasks
curl https://YOUR_USERNAME-customer-support-env.hf.space/tasks

# Response:
{
  "classify": {
    "description": "Classify ticket category and priority",
    "action_schema": "{...}"
  },
  ...
}
```

---

## Monitoring & Debugging

### View Logs

1. Go to Space settings
2. Click **Logs** tab
3. See stderr/stdout output

### Common Issues

| Issue | Solution |
|-------|----------|
| "GROQ_API_KEY not set" | Add secret in Space settings → Restart |
| 502 Bad Gateway | Space is still building (wait 5 min) |
| Import errors | Check all files copied to Space |
| Memory exceeded | Downgrade to CPU or slim hardware |

### Performance Notes

- **CPU basic** (free): ~2-5 sec per inference
- **Recommended for demo**: CPU basic is fine
- **For prod**: Consider GPU tier (paid)

---

## Updating Your Space

After local development:

```bash
# Make changes locally
# Test with Docker locally

# Push to HuggingFace
git add .
git commit -m "Updated reward function"
git push origin main

# Space auto-rebuilds and restarts
```

---

## Sharing Your Space

Once deployed:

1. **Direct link**: `https://huggingface.co/spaces/YOUR_USERNAME/customer-support-env`
2. **Share settings**: Space settings → Space info → Make public/private
3. **Embed in website**:
   ```html
   <iframe
     src="https://YOUR_USERNAME-customer-support-env.hf.space"
     width="100%"
     height="800">
   </iframe>
   ```

---

## API Authentication (Optional)

To add authentication:

1. Generate HuggingFace API token: https://huggingface.co/settings/tokens
2. Add to Space secrets: `HF_API_KEY`
3. Update `server/app.py`:
   ```python
   from fastapi.security import HTTPBearer
   
   security = HTTPBearer()
   
   @app.post("/step")
   async def step(action, credentials = Depends(security)):
       # Verify token...
   ```

---

## Cost

✅ **Completely FREE**:
- CPU basic: $0
- 48GB storage (included)
- Persistent app

**Optional paid tiers**:
- GPU: $7.50-60/month (for faster inference)
- Storage: $5/100GB (only if needed)

---

## Troubleshooting

### Build Failed

Check logs for Python errors:
```
ModuleNotFoundError: ...
```

**Fix**: Ensure all imports in `requirements.txt`:
```bash
pip freeze > requirements.txt
git add requirements.txt
git push origin main
```

### Space Times Out

Groq API might be slow. Add timeouts:
```python
# In server/app.py
timeout=30  # seconds
```

### Port Already in Use

HuggingFace automatically assigns port. Don't worry about local conflicts.

---

## Next Steps

1. ✅ Deploy to HuggingFace Spaces
2. 📊 Share baseline results in README
3. 🔗 Link Space in GitHub repo
4. 📈 Add model comparison examples
5. 🚀 Train your own agent & benchmark

---

## Example Space URL

Once complete, your Space lives at:

```
https://huggingface.co/spaces/YOUR_USERNAME/customer-support-env
```

**Interactive API docs**: `https://YOUR_USERNAME-customer-support-env.hf.space/docs`

---

## Questions?

- **HuggingFace Spaces docs**: https://huggingface.co/docs/hub/spaces-overview
- **Docker troubleshooting**: https://docs.docker.com/
- **FastAPI docs**: https://fastapi.tiangolo.com/

---

**Happy deploying!** 🚀
