import os


# Skip live API integration script during pytest collection unless explicitly configured.
if not os.getenv("GROQ_API_KEY"):
    collect_ignore = ["test_groq_integration.py"]
