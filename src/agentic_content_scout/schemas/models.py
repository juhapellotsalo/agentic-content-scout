"""Domain models for the ContentScout system."""

from typing import Literal

from pydantic import BaseModel, Field
from langchain.agents import AgentState
from typing_extensions import NotRequired


class MultiAgentState(AgentState):
    """Extended state for multi-agent handoff pattern.

    Inherits messages from AgentState, adds:
    - active_agent: Which agent config is currently active
    - topic_context: Accumulated context during topic creation HITL
    """

    active_agent: NotRequired[str]  # "supervisor" | "topic_manager" | "content_scout"
    topic_context: NotRequired[dict]  # Accumulated preferences during HITL


class ScoutState(AgentState):
    """State for the ContentScout subgraph.

    Flows through: load_context → search_evaluate → save_articles
    """

    # Input (from handoff)
    task: NotRequired[str]  # What to search for
    topic_slug: NotRequired[str]  # Which topic to scout

    # Loaded by load_context node
    preferences: NotRequired[str]  # Topic preferences.md content
    saved_urls: NotRequired[list[str]]  # Already saved URLs

    # Output from search_evaluate node
    recommended: NotRequired[list[dict]]  # Articles to save: [{url, title, reason}]

    # Final output
    summary: NotRequired[str]  # Summary for supervisor


class CuratedArticle(BaseModel):
    """A curated article with reasoning."""

    url: str
    title: str
    reason: str = Field(description="Why this article was selected")


class CurationOutput(BaseModel):
    """Structured output from content curation."""

    articles: list[CuratedArticle] = Field(description="The curated articles (4-5 max)")
    summary: str = Field(description="Brief summary of what was found")


class TopicResult(BaseModel):
    """Structured result from TopicManager operations."""

    operation: Literal["list", "create", "get", "update", "rename", "delete"] = Field(
        description="The operation that was performed"
    )
    topics: list[str] | None = Field(
        default=None, description="List of topic slugs (for list operation)"
    )
    slug: str | None = Field(
        default=None, description="The topic slug (for create/get/update/delete)"
    )
    content: str | None = Field(
        default=None, description="The topic preferences content (for get operation)"
    )
    success: bool = Field(
        default=True, description="Whether the operation succeeded"
    )
    message: str | None = Field(
        default=None, description="Optional message about the operation"
    )
