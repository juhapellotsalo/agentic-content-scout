"""Supervisor - router agent that delegates to specialized agents."""

from agentic_content_scout.tools import handoff_to_scout, handoff_to_topics, reflect

from .base import HandoffAgent

SYSTEM_PROMPT = """You are the assistant for a personalized content aggregator.

## Role
Route user requests to the appropriate agent.

## When to Hand Off
- handoff_to_topics: Creating, updating, deleting, viewing topics or preferences
- handoff_to_scout: Finding content, searching for articles, scouting new sources

## Direct Response
Only respond directly for general questions or greetings.

## After Handoff Returns
- TopicManager: acknowledge what was done briefly
- ContentScout: report what was found/saved
- Pass through content, don't add suggestions
"""


class Supervisor(HandoffAgent):
    """Router agent that delegates to specialized agents."""

    name = "supervisor"
    system_prompt = SYSTEM_PROMPT
    tools = [reflect, handoff_to_topics, handoff_to_scout]
    use_smart_model = False  # Simple routing doesn't need reasoning model
