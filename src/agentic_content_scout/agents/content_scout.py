"""ContentScout - finds and saves content for topics.

Uses a subgraph architecture:
- resolve_topic: Resolve topic slug with LLM + HITL if ambiguous (1 LLM call)
- load_context: Load topic preferences and saved URLs (no LLM)
- search_evaluate: Focused ReAct with just search tool (2-4 LLM calls)
- save_articles: Save recommendations to disk (no LLM)
"""

import json
import re
from datetime import date
from pathlib import Path

import yaml
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from agentic_content_scout.llm.openai import get_mini_model
from agentic_content_scout.schemas import MultiAgentState, ScoutState
from agentic_content_scout.tools import tavily_search
from agentic_content_scout.utils import ToolActionsLogger


TOPICS_DIR = Path(__file__).parent.parent.parent.parent / "topics"


class TopicResolution(BaseModel):
    """Result of topic resolution."""
    slug: str | None = Field(description="The resolved topic slug, or null if ambiguous/not found")
    confidence: str = Field(description="'high' if certain, 'low' if ambiguous or unsure")
    reason: str = Field(description="Brief explanation of the resolution")


def _get_available_topics() -> list[str]:
    """Get list of available topic slugs."""
    topics = []
    for path in TOPICS_DIR.iterdir():
        if path.is_dir() and (path / "preferences.md").exists():
            topics.append(path.name)
    return sorted(topics)


def _resolve_topic(state: ScoutState) -> dict:
    """Resolve topic slug from user input. Uses LLM + HITL if ambiguous."""
    task = state.get("task", "")
    topic_hint = state.get("topic_slug", "")
    available_topics = _get_available_topics()

    if not available_topics:
        # No topics exist - interrupt to inform user
        response = interrupt({
            "question": "No topics found. Please create a topic first using the topic manager."
        })
        return {"topic_slug": None}

    # Mini model is sufficient for simple topic matching
    model = get_mini_model()
    prompt = f"""Given the user's task and available topics, determine which topic they want.

User's task: {task}
Topic hint from user: {topic_hint}

Available topics: {', '.join(available_topics)}

Return the best matching topic slug, or null if unclear."""

    result = model.with_structured_output(TopicResolution).invoke(
        prompt,
        config={"run_name": "resolve_topic_llm"},
    )

    # If high confidence, proceed
    if result.confidence == "high" and result.slug in available_topics:
        return {"topic_slug": result.slug}

    # Low confidence or not found - ask user
    if result.slug and result.slug in available_topics:
        question = f"Did you mean the '{result.slug}' topic? (yes/no, or type a different topic name)"
    else:
        question = f"Which topic? Available: {', '.join(available_topics)}"

    response = interrupt({"question": question})

    # Process user response
    response_lower = response.lower().strip()
    if response_lower in ("yes", "y") and result.slug:
        return {"topic_slug": result.slug}

    # Check if response matches a topic
    for topic in available_topics:
        if response_lower == topic or response_lower in topic or topic in response_lower:
            return {"topic_slug": topic}

    # Couldn't resolve - return None (will fail gracefully)
    return {"topic_slug": None}


SEARCH_EVALUATE_PROMPT = """You find the single best new content for a topic.

## Context
Preferences:
{preferences}

Already saved (skip these URLs):
{saved_urls}

## Your Task
{task}

## Process
1. Formulate 1-2 targeted search queries based on the preferences
2. Call search() with your queries
3. Evaluate results against the preference criteria
4. Select the ONE best match that isn't already saved

## Output Format
When done, respond with ONLY this JSON (no other text):
```json
{{
  "articles": [
    {{"url": "...", "title": "...", "reason": "Why this is the best match"}}
  ],
  "summary": "Brief description of what was found"
}}
```
"""


# --- Subgraph Nodes ---


def _load_context(state: ScoutState) -> dict:
    """Load topic preferences and saved URLs. No LLM call."""
    topic_slug = state.get("topic_slug", "")

    # Load preferences
    prefs_file = TOPICS_DIR / topic_slug / "preferences.md"
    preferences = prefs_file.read_text() if prefs_file.exists() else "No preferences found."

    # Load saved URLs
    links_file = TOPICS_DIR / topic_slug / "links.yaml"
    saved_urls = []
    if links_file.exists():
        with open(links_file) as f:
            links = yaml.safe_load(f) or []
            saved_urls = [link["url"] for link in links]

    return {
        "preferences": preferences,
        "saved_urls": saved_urls,
    }


def _search_evaluate(state: ScoutState) -> dict:
    """Focused ReAct agent with just search tool. 2-4 LLM calls max."""
    preferences = state.get("preferences", "")
    saved_urls = state.get("saved_urls", [])
    task = state.get("task", "Find relevant content")

    # Format the prompt with context
    system_prompt = SEARCH_EVALUATE_PROMPT.format(
        preferences=preferences,
        saved_urls="\n".join(f"- {url}" for url in saved_urls) if saved_urls else "(none)",
        task=task,
    )

    # Create focused agent with just search tool
    agent = create_agent(
        model=get_mini_model(),
        tools=[tavily_search],
        system_prompt=system_prompt,
    )

    # Run agent
    logger = ToolActionsLogger()
    result = agent.invoke(
        {"messages": [HumanMessage(content=task)]},
        config={
            "callbacks": [logger],
            "run_name": "content_scout_search",  # Identify in LangSmith
        },
    )

    # Extract recommendations from last AI message
    recommended = []
    summary = "No articles found."

    messages = result.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            # Try to parse JSON from the response
            content = msg.content
            try:
                # Look for JSON block in response
                json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(1))
                else:
                    # Try parsing the whole content as JSON
                    data = json.loads(content)

                recommended = data.get("articles", [])
                summary = data.get("summary", "Found articles.")
            except json.JSONDecodeError:
                # If JSON parsing fails, treat as summary
                summary = content[:500]
            break

    return {
        "recommended": recommended,
        "summary": summary,
        # Don't pass messages - they're internal to the search agent
    }


def _save_articles(state: ScoutState) -> dict:
    """Save recommended articles to links.yaml. No LLM call."""
    topic_slug = state.get("topic_slug", "")
    recommended = state.get("recommended", [])

    if not recommended:
        return {"summary": state.get("summary", "No articles found to save.")}

    links_file = TOPICS_DIR / topic_slug / "links.yaml"
    today = date.today().isoformat()

    # Load existing
    existing = []
    if links_file.exists():
        with open(links_file) as f:
            existing = yaml.safe_load(f) or []

    existing_urls = {link.get("url") for link in existing}

    # Add new articles
    saved_count = 0
    for article in recommended:
        url = article.get("url", "")
        if url and url not in existing_urls:
            existing.append({
                "title": article.get("title", "Untitled"),
                "url": url,
                "reason": article.get("reason", ""),
                "date": today,
            })
            saved_count += 1

    # Write back
    if saved_count > 0:
        with open(links_file, "w") as f:
            yaml.dump(existing, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Update summary with saved URLs
    original_summary = state.get("summary", "")
    if saved_count > 0:
        saved_urls = [a.get("url") for a in recommended if a.get("url") not in existing_urls][:saved_count]
        urls_text = "\n".join(f"  → {url}" for url in saved_urls)
        summary = f"{original_summary}\n\nSaved to {topic_slug}:\n{urls_text}"
    else:
        summary = f"{original_summary}\n\nNo new articles to save (duplicates filtered)."

    return {"summary": summary}


def _build_scout_graph():
    """Build the ContentScout subgraph."""
    builder = StateGraph(ScoutState)

    builder.add_node("resolve_topic", _resolve_topic)
    builder.add_node("load_context", _load_context)
    builder.add_node("search_evaluate", _search_evaluate)
    builder.add_node("save_articles", _save_articles)

    builder.add_edge(START, "resolve_topic")
    builder.add_edge("resolve_topic", "load_context")
    builder.add_edge("load_context", "search_evaluate")
    builder.add_edge("search_evaluate", "save_articles")
    builder.add_edge("save_articles", END)

    return builder.compile()


# --- ContentScout Agent ---


class ContentScout:
    """Agent that finds and saves content for topics using a subgraph."""

    name = "content_scout"

    def __init__(self):
        self._graph = None

    @property
    def graph(self):
        """Lazy-build the subgraph."""
        if self._graph is None:
            self._graph = _build_scout_graph()
        return self._graph

    def invoke(self, state: MultiAgentState) -> dict:
        """Run the scout subgraph and return results for handoff."""
        # Extract task and topic_slug from topic_context
        topic_context = state.get("topic_context", {})
        task = topic_context.get("task", "Find relevant content")
        topic_slug = topic_context.get("topic_slug", "")

        # Run the scout subgraph
        result = self.graph.invoke(
            {
                "task": task,
                "topic_slug": topic_slug,
                "messages": [],
            },
            config={"run_name": "content_scout_subgraph"},
        )

        # Extract summary from result
        summary = result.get("summary", "Scout completed.")

        # Return AIMessage (not ToolMessage - the handoff already responded to the tool call)
        return {
            "active_agent": "supervisor",
            "messages": [
                AIMessage(content=summary),
            ],
            "topic_context": {},
        }
