"""Preferences loading utilities."""

from pathlib import Path


def load_preferences(topic_slug: str) -> str:
    """
    Load default preferences + topic-specific preferences.

    Args:
        topic_slug: The topic directory name (e.g., 'agentic-coding-tools')

    Returns:
        Combined preferences content as a string
    """
    topics_dir = Path(__file__).parent.parent.parent.parent / "topics"

    # Load default preferences
    default_prefs = topics_dir / "default_preferences.md"
    content = default_prefs.read_text() if default_prefs.exists() else ""

    # Load topic-specific preferences
    topic_prefs = topics_dir / topic_slug / "preferences.md"
    if topic_prefs.exists():
        content += "\n\n" + topic_prefs.read_text()

    return content


def main():
    """Display preferences content for a given topic."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m agentic_content_scout.utils.preferences <topic_slug>")
        sys.exit(1)

    topic_slug = sys.argv[1]
    preferences = load_preferences(topic_slug)

    if preferences:
        print(preferences)
    else:
        print(f"No preferences found for topic: {topic_slug}")


if __name__ == "__main__":
    main()