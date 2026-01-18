"""Content discovery and storage tools."""

from datetime import date
from pathlib import Path

import yaml
from langchain_core.tools import tool

TOPICS_DIR = Path(__file__).parent.parent.parent.parent / "topics"


@tool
def save_article(slug: str, title: str, url: str, reason: str) -> str:
    """Save a discovered article to a topic's links file.

    Args:
        slug: The topic slug to save to
        title: Article title
        url: Article URL
        reason: Why this article was selected

    Returns:
        Confirmation message or error
    """
    topic_dir = TOPICS_DIR / slug
    if not topic_dir.exists():
        return f"Topic '{slug}' not found."

    links_file = topic_dir / "links.yaml"
    today = date.today().isoformat()

    # Load existing links
    existing = []
    if links_file.exists():
        with open(links_file) as f:
            existing = yaml.safe_load(f) or []

    # Check for duplicate
    if any(link.get("url") == url for link in existing):
        return f"Article already saved: {url}"

    # Append new article
    existing.append({
        "title": title,
        "url": url,
        "reason": reason,
        "date": today,
    })

    with open(links_file, "w") as f:
        yaml.dump(existing, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return f"Saved '{title}' to {slug}."


@tool
def get_saved_urls(slug: str) -> str:
    """Get URLs already saved for a topic (to avoid duplicates).

    Args:
        slug: The topic slug

    Returns:
        List of saved URLs or message if none
    """
    links_file = TOPICS_DIR / slug / "links.yaml"

    if not links_file.exists():
        return "No saved articles yet."

    with open(links_file) as f:
        links = yaml.safe_load(f) or []

    if not links:
        return "No saved articles yet."

    urls = [link["url"] for link in links]
    return "Already saved:\n" + "\n".join(f"- {url}" for url in urls)
