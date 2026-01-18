"""TopicManager - handles topic CRUD with adaptive HITL."""

from agentic_content_scout.tools import (
    create_topic,
    delete_topic,
    gather_preferences,
    get_topic,
    handoff_to_supervisor,
    list_topics,
    reflect,
    update_topic,
)

from .base import HandoffAgent

SYSTEM_PROMPT = """You are the TopicManager. Handle topic CRUD.

## Rules
- Act immediately with tool calls - don't narrate what you'll do
- When user references a topic by name, list_topics first to find the correct slug
- If user's request is clear and complete, just do it - don't ask for confirmation
- Only use gather_preferences when info is genuinely missing
- Slugs: lowercase with hyphens (e.g., "AI Safety" → "ai-safety")
- After write operations (create/update/delete): handoff_to_supervisor with brief summary
- After read operations (list/get): handoff_to_supervisor with the actual content

## Preferences Format (markdown)
# Topic Name
## Focus - what to track
## Sources - Prefer: ... / Avoid: ...
## Guidance - priorities and filters
"""


class TopicManager(HandoffAgent):
    """Agent that manages content topics via handoff pattern."""

    name = "topic_manager"
    system_prompt = SYSTEM_PROMPT
    tools = [
        reflect,
        gather_preferences,
        list_topics,
        create_topic,
        get_topic,
        update_topic,
        delete_topic,
        handoff_to_supervisor,
    ]
