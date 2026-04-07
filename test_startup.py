#!/usr/bin/env python3
"""Test if app starts without hanging"""
import sys
import time
from threading import Thread

def start_app():
    try:
        import uvicorn
        from customer_support_env.server.app import app
        print("[TEST] Starting uvicorn...", flush=True)
        uvicorn.run(app, host="0.0.0.0", port=7860, log_level="info")
    except Exception as e:
        print(f"[ERROR] {e}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    thread = Thread(target=start_app, daemon=True)
    thread.start()
    
    # Wait up to 5 seconds for startup
    time.sleep(5)
    
    if thread.is_alive():
        print("[TIMEOUT] App is still starting after 5 seconds - possible hang!")
        sys.exit(1)
    else:
        print("[OK] App started successfully")
        sys.exit(0)
