#!/usr/bin/env python3
"""Check available Groq models."""

import os
from groq import Groq

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("ERROR: GROQ_API_KEY not set")
    exit(1)

client = Groq(api_key=api_key)

try:
    models = client.models.list()
    print("Available Groq models:")
    print("=" * 60)
    for model in models.data:
        print(f"  - {model.id}")
except Exception as e:
    print(f"ERROR: {e}")
