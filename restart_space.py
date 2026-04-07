#!/usr/bin/env python3
"""Restart HF Space with production changes"""
import os
import requests

token = os.getenv("HF_TOKEN")
if not token:
    print("❌ HF_TOKEN not set")
    exit(1)

repo_id = "kavyabumiya/openenv"
url = f"https://huggingface.co/api/spaces/{repo_id}/restart"

print(f"🚀 Restarting HF Space: {repo_id}")
print(f"📍 Endpoint: {url}")

try:
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={},
        timeout=10
    )
    
    if response.status_code in [200, 201, 202]:
        print("✅ Space restart request sent successfully!")
        print(f"Response: {response.json()}")
    else:
        print(f"⚠️  Unexpected status: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print("\n⏳ Space is restarting...")
print("📊 Expected timeline:")
print("  - 0-2 min: Docker build")
print("  - 2-5 min: Pip install")
print("  - 5-10 min: Application startup with NEW logging")
print("\n✨ Go to: https://huggingface.co/spaces/kavyabumiya/openenv")
print("📝 Watch logs for real-time uvicorn startup messages")
