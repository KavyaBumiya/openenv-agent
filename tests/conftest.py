import os


# Skip live API integration script during pytest collection unless explicitly configured.
if not os.getenv("HF_TOKEN"):
    collect_ignore = ["test_live_integration.py"]
