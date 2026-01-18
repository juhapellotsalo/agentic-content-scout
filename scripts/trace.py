#!/usr/bin/env python3
"""Fetch and display LangSmith trace summaries."""

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from langsmith import Client


def get_latest_traces(limit: int = 1, project: str = "agentic-content-scout"):
    """Fetch the latest LangGraph traces."""
    client = Client()

    runs = list(client.list_runs(
        project_name=project,
        filter='eq(name, "LangGraph")',
        limit=limit,
    ))

    return runs


def print_trace_summary(run, verbose: bool = False):
    """Print a summary of a trace run."""
    print(f"{'=' * 50}")
    print(f"Run ID: {run.id}")
    print(f"Status: {run.status}")
    print(f"Time: {run.start_time} → {run.end_time}")

    if run.end_time and run.start_time:
        duration = (run.end_time - run.start_time).total_seconds()
        print(f"Duration: {duration:.1f}s")

    print()
    print(f"Total tokens:      {run.total_tokens or 0:,}")
    print(f"  Prompt tokens:   {run.prompt_tokens or 0:,}")
    print(f"  Completion:      {run.completion_tokens or 0:,}")

    if run.total_cost:
        print(f"Cost: ${run.total_cost:.4f}")

    child_count = len(run.child_run_ids) if run.child_run_ids else 0
    print(f"Child runs: {child_count}")

    if verbose and run.inputs:
        print()
        print("Input:")
        messages = run.inputs.get("messages", [])
        for msg in messages[:3]:  # First 3 messages
            content = msg.get("content", "")[:100]
            print(f"  [{msg.get('type', '?')}] {content}...")

    if verbose and run.outputs:
        print()
        print("Output:")
        messages = run.outputs.get("messages", [])
        if messages:
            last = messages[-1]
            content = last.get("content", "")[:200]
            print(f"  [{last.get('type', '?')}] {content}...")


def main():
    parser = argparse.ArgumentParser(description="Fetch LangSmith trace summaries")
    parser.add_argument("-n", "--limit", type=int, default=1, help="Number of traces to fetch")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show input/output snippets")
    parser.add_argument("-p", "--project", default="agentic-content-scout", help="Project name")
    args = parser.parse_args()

    runs = get_latest_traces(limit=args.limit, project=args.project)

    if not runs:
        print("No LangGraph runs found.")
        return

    for run in runs:
        print_trace_summary(run, verbose=args.verbose)
        print()


if __name__ == "__main__":
    main()
