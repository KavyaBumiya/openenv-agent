#!/usr/bin/env python3
"""Generate benchmark report in JSON format.

This script runs the official baseline benchmark and generates a structured
JSON report that can be integrated into CI/CD pipelines.

Usage:
    python generate_benchmark_report.py --output report.json --mode official
    
Output:
    - report.json: Detailed benchmark results
    - report_summary.json: High-level summary
    - Console output: Formatted results table
"""

import json
import sys
import os
import argparse
from datetime import datetime

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load from .env file
except ImportError:
    pass  # dotenv not installed
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from customer_support_env.baseline import run_baseline


def generate_report(mode: str = "official", output_dir: str = ".") -> dict:
    """Generate and save benchmark report.
    
    Args:
        mode: "official" or "training"
        output_dir: Directory to save report files
    
    Returns:
        Dictionary with report results
    """
    
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"BENCHMARK REPORT GENERATION")
    print(f"Mode: {mode.upper()}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*70}\n")
    
    # Run baseline
    results = run_baseline(mode=mode)
    
    # Create structured report
    report = {
        "generated_at": datetime.now().isoformat(),
        "mode": mode,
        "model": results.get("model"),
        "provider": results.get("provider"),
        "temperature_strategy": results.get("temperature_strategy"),
        "episodes_per_task": results.get("episodes_per_task"),
        "tasks": results.get("tasks", {}),
        "overall": results.get("overall", {}),
    }
    
    # Create summary for quick reference
    summary = {
        "mode": mode,
        "generated_at": datetime.now().isoformat(),
        "overall_mean": report["overall"].get("mean", 0),
        "overall_min": report["overall"].get("min", 0),
        "overall_max": report["overall"].get("max", 0),
        "task_means": {
            task: data.get("mean", 0) 
            for task, data in report["tasks"].items()
        },
        "task_counts": {
            task: len(data.get("scores", []))
            for task, data in report["tasks"].items()
        },
        "errors_total": sum(
            data.get("errors", 0)
            for data in report["tasks"].values()
        ),
    }
    
    # Save full report
    report_file = output_path / f"report_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"✓ Saved full report: {report_file}")
    
    # Save summary
    summary_file = output_path / f"report_summary_{mode}.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"✓ Saved summary: {summary_file}")
    
    # Print formatted summary
    print_formatted_summary(summary, report)
    
    return report


def print_formatted_summary(summary: dict, report: dict):
    """Print nicely formatted benchmark summary."""
    
    print(f"\n{'='*70}")
    print("📊 BENCHMARK SUMMARY")
    print(f"{'='*70}\n")
    
    print("📈 Overall Performance:")
    print(f"  Mean Score:  {summary['overall_mean']:.1%}")
    print(f"  Min Score:   {summary['overall_min']:.1%}")
    print(f"  Max Score:   {summary['overall_max']:.1%}")
    
    print("\n📋 Per-Task Breakdown:")
    for task in ["classify", "route", "resolve"]:
        if task in summary["task_means"]:
            mean = summary["task_means"][task]
            count = summary["task_counts"][task]
            task_data = report["tasks"].get(task, {})
            task_min = task_data.get("min", 0)
            task_max = task_data.get("max", 0)
            
            print(f"\n  {task.upper()}:")
            print(f"    Episodes: {count}")
            print(f"    Mean:     {mean:.1%}")
            print(f"    Range:    {task_min:.1%} → {task_max:.1%}")
            print(f"    Std Dev:  {task_data.get('std', 0):.3f}")
            if task_data.get("errors", 0):
                print(f"    Errors:   {task_data.get('errors', 0)}")
    
    if summary["errors_total"]:
        print(f"\n⚠️  Total Errors: {summary['errors_total']}")
    
    print(f"\n{'='*70}\n")


def save_github_actions_output(report: dict, output_file: str = "benchmark_output.json"):
    """Save report in GitHub Actions compatible format.
    
    This can be used to set output variables for downstream jobs.
    """
    
    overall = report.get("overall", {})
    
    # Create GitHub Actions output
    github_output = {
        "status": "success" if overall.get("mean", 0) > 0 else "failed",
        "overall_mean_score": overall.get("mean", 0),
        "overall_min_score": overall.get("min", 0),
        "overall_max_score": overall.get("max", 0),
        "timestamp": datetime.now().isoformat(),
    }
    
    # Add per-task scores
    for task, data in report.get("tasks", {}).items():
        github_output[f"task_{task}_mean"] = data.get("mean", 0)
        github_output[f"task_{task}_episodes"] = len(data.get("scores", []))
    
    with open(output_file, "w") as f:
        json.dump(github_output, f, indent=2)
    
    print(f"✓ GitHub Actions output saved: {output_file}")
    
    return github_output


def compare_reports(before_file: str, after_file: str):
    """Compare two benchmark reports to show improvement/regression.
    
    Args:
        before_file: Path to earlier report
        after_file: Path to later report
    """
    
    with open(before_file, "r") as f:
        before = json.load(f)
    
    with open(after_file, "r") as f:
        after = json.load(f)
    
    print(f"\n{'='*70}")
    print("📊 BENCHMARK COMPARISON")
    print(f"{'='*70}\n")
    
    before_mean = before.get("overall", {}).get("mean", 0)
    after_mean = after.get("overall", {}).get("mean", 0)
    improvement = after_mean - before_mean
    pct_improvement = (improvement / before_mean * 100) if before_mean > 0 else 0
    
    print(f"Previous Mean: {before_mean:.1%}")
    print(f"Current Mean:  {after_mean:.1%}")
    
    if improvement > 0:
        print(f"✓ Improvement: +{improvement:.1%} ({pct_improvement:+.1f}%)")
    elif improvement < 0:
        print(f"✗ Regression:  {improvement:.1%} ({pct_improvement:+.1f}%)")
    else:
        print(f"= No change:   {improvement:.1%}")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate benchmark report for CI/CD integration"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".",
        help="Output directory for report files (default: current directory)"
    )
    parser.add_argument(
        "--mode",
        choices=["official", "training"],
        default="official",
        help="Benchmark mode (default: official)"
    )
    parser.add_argument(
        "--github-actions",
        action="store_true",
        help="Generate GitHub Actions compatible output"
    )
    parser.add_argument(
        "--compare-to",
        type=str,
        help="Compare with previous report (path to report JSON)"
    )
    
    args = parser.parse_args()
    
    # Check API key
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY environment variable not set")
        sys.exit(1)
    
    # Generate report
    report = generate_report(mode=args.mode, output_dir=args.output)
    
    # Generate GitHub Actions output if requested
    if args.github_actions:
        save_github_actions_output(report)
    
    # Compare if requested
    if args.compare_to:
        latest_report = list(Path(args.output).glob("report_*.json"))[0]
        compare_reports(args.compare_to, str(latest_report))
    
    print("✓ Report generation complete!")
