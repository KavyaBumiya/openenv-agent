#!/usr/bin/env python
"""
Official Benchmark Script
=========================

This script runs the OFFICIAL reproducible baseline for judging.

Use this to generate the canonical scores for your submission.

Features:
- Low temperature (0.1 all tasks) for reproducibility
- Full dataset sweep (30 episodes per task)
- Deterministic seeding (same scores every run)
- Clean JSON output for parsing

Usage:
    python run_official_benchmark.py

Requirements:
    - GROQ_API_KEY environment variable set (or .env file)
    - groq Python package installed
    - All customer_support_env files present

Output:
    - Prints detailed score breakdown
    - Outputs JSON with mean/min/max per task
    - Can be captured and compared across runs
"""

import sys
import os

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load from .env file in current directory
except ImportError:
    pass  # dotenv not installed, skip

# Ensure we can import from the environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from customer_support_env.baseline import run_baseline


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      OFFICIAL BENCHMARK (REPRODUCIBLE)                       ║
║                                                                              ║
║  Temperature: 0.1 (all tasks) — deterministic, judge-safe                   ║
║  Dataset: Full sweep (30 episodes per task)                                 ║
║  Validation: Run this before submission to ensure scoring works             ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        results = run_baseline(mode="official")
        
        print("\n" + "=" * 80)
        print("OFFICIAL BASELINE COMPLETE")
        print("=" * 80)
        print(f"""
These scores are reproducible and judge-ready.

Mean scores by task:
  - Classify (EASY):   {results['tasks']['classify']['mean']:.1%}
  - Route (MEDIUM):    {results['tasks']['route']['mean']:.1%}
  - Resolve (HARD):    {results['tasks']['resolve']['mean']:.1%}

Overall mean:        {results['overall']['mean']:.1%}

To run again and verify reproducibility:
  python run_official_benchmark.py
""")
        
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}", file=sys.stderr)
        sys.exit(1)
