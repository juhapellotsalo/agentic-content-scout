"""Topic management tools."""

import shutil
from pathlib import Path

import yaml
from langchain_core.tools import tool
from langgraph.types import interrupt

TOPICS_DIR = Path(__file__).parent.parent.parent.parent / "topics"


@tool
def gather_preferences(question: str) -> str:
    """Ask the user a question to gather topic preferences.

    Use this during topic creation to collect information about:
    - What aspects of the topic interest them
    - Sources to prefer or avoid
    - Content to prioritize or skip

    The conversation will pause until the user responds.

    Args:
        question: A conversational question to ask the user

    Returns:
        The user's response
    """
    response = interrupt({"question": question})
    return response


def get_topic_slugs() -> list[str]:
    """Get list of topic slugs (internal helper, no tracing)."""
    topics = []
    for path in TOPICS_DIR.iterdir():
        if path.is_dir() and (path / "preferences.md").exists():
            topics.append(path.name)
    return sorted(topics)


@tool
def list_topics() -> str:
    """List all tracked topics.

    Returns a list of topic slugs (directory names) that have preferences.md files.
    """
    topics = get_topic_slugs()

    if not topics:
        return "No topics found."

    return "Topics:\n" + "\n".join(f"- {t}" for t in topics)


@tool
def create_topic(slug: str, preferences_content: str) -> str:
    """Create a new topic with the provided preferences content.

    Args:
        slug: URL-friendly name for the topic (e.g., 'ai-safety-research')
        preferences_content: The full preferences.md content to write

    Returns:
        Confirmation message or error
    """
    topic_dir = TOPICS_DIR / slug

    if topic_dir.exists():
        return f"Topic '{slug}' already exists."

    topic_dir.mkdir(parents=True)
    (topic_dir / "preferences.md").write_text(preferences_content)

    return f"Created topic '{slug}'."


@tool
def delete_topic(slug: str) -> str:
    """Delete a topic and all its files.

    Args:
        slug: The topic slug to delete

    Returns:
        Confirmation message or error
    """
    topic_dir = TOPICS_DIR / slug

    if not topic_dir.exists():
        return f"Topic '{slug}' not found."

    if not (topic_dir / "preferences.md").exists():
        return f"'{slug}' exists but has no preferences.md - not a valid topic."

    shutil.rmtree(topic_dir)
    return f"Deleted topic '{slug}'."


@tool
def get_topic(slug: str) -> str:
    """Get the full state of a topic: preferences and saved links.

    Args:
        slug: The topic slug to read

    Returns:
        The topic preferences and saved links, or error message
    """
    topic_dir = TOPICS_DIR / slug
    prefs_file = topic_dir / "preferences.md"

    if not prefs_file.exists():
        return f"Topic '{slug}' not found."

    # Read preferences
    result = prefs_file.read_text()

    # Read links if they exist
    links_file = topic_dir / "links.yaml"
    if links_file.exists():
        links = yaml.safe_load(links_file.read_text()) or []
        if links:
            result += "\n\n## Saved Links\n"
            for link in links:
                title = link.get("title", "Untitled")
                url = link.get("url", "")
                result += f"- [{title}]({url})\n"
        else:
            result += "\n\n## Saved Links\nNo links saved yet."
    else:
        result += "\n\n## Saved Links\nNo links saved yet."

    return result


@tool
def update_topic(slug: str, preferences_content: str) -> str:
    """Update a topic's preferences by rewriting the entire file.

    Use get_topic first to read the current preferences, then modify as needed.

    Args:
        slug: The topic slug to update
        preferences_content: The complete new preferences.md content

    Returns:
        Confirmation message or error
    """
    topic_dir = TOPICS_DIR / slug
    prefs_file = topic_dir / "preferences.md"

    if not prefs_file.exists():
        return f"Topic '{slug}' not found."

    prefs_file.write_text(preferences_content)
    return f"Updated preferences for '{slug}'."


def to_slug(name: str) -> str:
    """Convert a name to a URL-friendly slug."""
    return name.lower().strip().replace(" ", "-")


@tool
def rename_topic(old_slug: str, new_name: str) -> str:
    """Rename a topic to a new name.

    The new name will be converted to a slug (lowercase, spaces to hyphens).

    Args:
        old_slug: The current topic slug
        new_name: The new name for the topic (will be slugified)

    Returns:
        Confirmation message or error
    """
    old_dir = TOPICS_DIR / old_slug
    if not old_dir.exists():
        return f"Topic '{old_slug}' not found."

    new_slug = to_slug(new_name)
    new_dir = TOPICS_DIR / new_slug

    if new_dir.exists():
        return f"Cannot rename: '{new_slug}' already exists."

    old_dir.rename(new_dir)
    return f"Renamed '{old_slug}' to '{new_slug}'."


def main():
    """CLI for testing topic tools."""
    import sys

    # When running directly, add src to path
    if __name__ == "__main__":
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    if len(sys.argv) < 2:
        print("Usage: python topics.py <command> [args]")
        print("Commands:")
        print("  list-topics")
        print("  create-topic <slug> <content|@file>")
        print("  get-topic <slug>")
        print("  update-topic <slug> <content|@file>")
        print("  delete-topic <slug>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list-topics":
        print(list_topics.invoke({}))

    elif command == "create-topic":
        if len(sys.argv) < 4:
            print("Usage: create-topic <slug> <content|@file>")
            sys.exit(1)
        slug = sys.argv[2]
        content = sys.argv[3]
        if content.startswith("@"):
            content = Path(content[1:]).read_text()
        print(create_topic.invoke({"slug": slug, "preferences_content": content}))

    elif command == "get-topic":
        if len(sys.argv) < 3:
            print("Usage: get-topic <slug>")
            sys.exit(1)
        slug = sys.argv[2]
        print(get_topic.invoke({"slug": slug}))

    elif command == "update-topic":
        if len(sys.argv) < 4:
            print("Usage: update-topic <slug> <content>")
            print("  (content can be a file path starting with @)")
            sys.exit(1)
        slug = sys.argv[2]
        content = sys.argv[3]
        # Support @filename to read content from file
        if content.startswith("@"):
            content = Path(content[1:]).read_text()
        print(update_topic.invoke({"slug": slug, "preferences_content": content}))

    elif command == "delete-topic":
        if len(sys.argv) < 3:
            print("Usage: delete-topic <slug>")
            sys.exit(1)
        slug = sys.argv[2]
        print(delete_topic.invoke({"slug": slug}))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
