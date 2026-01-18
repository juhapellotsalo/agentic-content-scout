"""Brief storage utilities."""

from datetime import date
from pathlib import Path

import yaml

from agentic_content_scout.schemas import CurationOutput

TOPICS_DIR = Path(__file__).parent.parent.parent.parent / "topics"


def load_brief(topic_slug: str) -> list[str]:
    """Load URLs already saved for a topic.

    Args:
        topic_slug: The topic to load URLs for

    Returns:
        List of URLs already in links.yaml
    """
    links_file = TOPICS_DIR / topic_slug / "links.yaml"

    if not links_file.exists():
        return []

    with open(links_file) as f:
        links = yaml.safe_load(f) or []

    return [link["url"] for link in links]


def save_brief(topic_slug: str, curation: CurationOutput) -> Path:
    """Append curated articles to a topic's links file.

    Args:
        topic_slug: The topic this brief is for
        curation: The curation output to save

    Returns:
        Path to the links file
    """
    topic_dir = TOPICS_DIR / topic_slug
    if not topic_dir.exists():
        raise ValueError(f"Topic '{topic_slug}' does not exist")

    links_file = topic_dir / "links.yaml"
    today = date.today().isoformat()

    # Load existing links
    existing = []
    if links_file.exists():
        with open(links_file) as f:
            existing = yaml.safe_load(f) or []

    # Get existing URLs to avoid duplicates
    existing_urls = {link["url"] for link in existing}

    # Append new articles
    for article in curation.articles:
        if article.url not in existing_urls:
            existing.append({
                "title": article.title,
                "url": article.url,
                "reason": article.reason,
                "date": today,
            })

    with open(links_file, "w") as f:
        yaml.dump(existing, f, default_flow_style=False, allow_unicode=True, sort_keys=False, default_style='"')

    return links_file