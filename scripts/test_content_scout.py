#!/usr/bin/env python3
"""Test ContentScout nodes in isolation or run full graph.

Usage:
    python scripts/test_content_scout.py resolve_topic
    python scripts/test_content_scout.py load_context
    python scripts/test_content_scout.py search_evaluate
    python scripts/test_content_scout.py save_articles
    python scripts/test_content_scout.py full
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from agentic_content_scout.agents.content_scout import (
    _resolve_topic,
    _load_context,
    _search_evaluate,
    _save_articles,
    _get_available_topics,
    _build_scout_graph,
)


def test_resolve_topic(task: str = "Find metroidvania articles", hint: str = ""):
    """Test topic resolution."""
    print("Available topics:", _get_available_topics())
    print()

    state = {"task": task, "topic_slug": hint}
    print(f"Input: {state}")
    result = _resolve_topic(state)
    print(f"Output: {result}")
    return result


def test_load_context():
    """Test context loading with resolved topic."""
    state = {"topic_slug": "metroidvania-games"}
    print(f"Input: {state}")
    result = _load_context(state)
    print(f"Output:")
    print(f"  preferences: {result['preferences'][:200]}...")
    print(f"  saved_urls: {len(result['saved_urls'])} URLs")
    for url in result['saved_urls'][:3]:
        print(f"    - {url[:60]}...")
    return result


def test_search_evaluate():
    """Test search/evaluate with loaded context."""
    # Simulate state after load_context
    state = {
        "task": "Find recent metroidvania articles",
        "preferences": "Focus on indie metroidvanias. Prefer design analysis over news.",
        "saved_urls": [],
    }
    print(f"Input task: {state['task']}")
    print(f"Input preferences: {state['preferences'][:100]}...")
    print()
    print("Running search agent (this makes LLM calls)...")
    result = _search_evaluate(state)
    print(f"\nOutput:")
    print(f"  summary: {result['summary']}")
    print(f"  recommended: {len(result.get('recommended', []))} articles")
    for article in result.get('recommended', [])[:3]:
        print(f"    - {article.get('title', 'No title')[:50]}")
    return result


def test_save_articles():
    """Test saving articles (dry run - doesn't actually save)."""
    state = {
        "topic_slug": "metroidvania-games",
        "recommended": [
            {"url": "https://example.com/test", "title": "Test Article", "reason": "Test"},
        ],
        "summary": "Found 1 test article.",
    }
    print(f"Input: {len(state['recommended'])} articles to save")
    print("NOTE: This would save to disk. Skipping actual save in test.")
    print(f"Would save to: topics/{state['topic_slug']}/links.yaml")
    return state


def test_full(task: str = "Find metroidvania articles", topic_slug: str = "metroidvania-games"):
    """Run the full scout subgraph."""
    graph = _build_scout_graph()

    initial_state = {
        "task": task,
        "topic_slug": topic_slug,
        "messages": [],
    }

    print(f"Running full scout graph...")
    print(f"  task: {task}")
    print(f"  topic_slug: {topic_slug}")
    print()

    result = graph.invoke(initial_state)

    print("Result:")
    print(f"  topic_slug: {result.get('topic_slug')}")
    print(f"  summary: {result.get('summary')}")
    print(f"  recommended: {len(result.get('recommended', []))} articles")
    for article in result.get('recommended', [])[:5]:
        print(f"    - {article.get('title', 'No title')[:60]}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Test ContentScout nodes")
    parser.add_argument("node", choices=["resolve_topic", "load_context", "search_evaluate", "save_articles", "full"])
    parser.add_argument("--task", default="Find metroidvania articles", help="Task description")
    parser.add_argument("--hint", default="", help="Topic hint for resolve_topic")
    parser.add_argument("--topic", default="metroidvania-games", help="Topic slug for full test")
    args = parser.parse_args()

    print(f"Testing: {args.node}")
    print("=" * 50)

    if args.node == "resolve_topic":
        test_resolve_topic(task=args.task, hint=args.hint)
    elif args.node == "load_context":
        test_load_context()
    elif args.node == "search_evaluate":
        test_search_evaluate()
    elif args.node == "save_articles":
        test_save_articles()
    elif args.node == "full":
        test_full(task=args.task, topic_slug=args.topic)


if __name__ == "__main__":
    main()
