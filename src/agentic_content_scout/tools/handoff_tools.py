"""Handoff tools for multi-agent transitions."""

from langchain.tools import tool, ToolRuntime
from langchain.messages import AIMessage, ToolMessage
from langgraph.types import Command


@tool
def handoff_to_topics(task: str, runtime: ToolRuntime) -> Command:
    """Hand off to TopicManager for topic operations.

    Use this when the user wants to:
    - Create, update, or delete topics
    - View or list topics
    - Modify topic preferences

    Args:
        task: Description of what the user wants to do with topics
    """
    last_ai_message = next(
        (msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)),
        None,
    )
    transfer_message = ToolMessage(
        content=f"Transferring to TopicManager: {task}",
        tool_call_id=runtime.tool_call_id,
    )

    messages = [last_ai_message, transfer_message] if last_ai_message else [transfer_message]

    return Command(
        goto="agent",
        update={
            "active_agent": "topic_manager",
            "messages": messages,
            "topic_context": {"task": task},
        },
        graph=Command.PARENT,
    )


@tool
def handoff_to_scout(task: str, topic_slug: str, runtime: ToolRuntime) -> Command:
    """Hand off to ContentScout for content discovery.

    Use this when the user wants to:
    - Find new content/articles for a topic
    - Search for something related to their interests
    - Scout or discover new sources

    Args:
        task: What the user wants to find
        topic_slug: The topic slug to scout (e.g., 'metroidvania', 'ai-safety')
    """
    last_ai_message = next(
        (msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)),
        None,
    )
    transfer_message = ToolMessage(
        content=f"Transferring to ContentScout: {task} (topic: {topic_slug})",
        tool_call_id=runtime.tool_call_id,
    )

    messages = [last_ai_message, transfer_message] if last_ai_message else [transfer_message]

    return Command(
        goto="agent",
        update={
            "active_agent": "content_scout",
            "messages": messages,
            "topic_context": {"task": task, "topic_slug": topic_slug},
        },
        graph=Command.PARENT,
    )


@tool
def handoff_to_supervisor(summary: str, runtime: ToolRuntime) -> Command:
    """Hand back to Supervisor when topic task is complete.

    Use this after completing a topic operation to return control
    to the main conversation.

    Args:
        summary: Brief summary of what was accomplished
    """
    last_ai_message = next(
        (msg for msg in reversed(runtime.state["messages"]) if isinstance(msg, AIMessage)),
        None,
    )
    transfer_message = ToolMessage(
        content=f"TopicManager completed: {summary}",
        tool_call_id=runtime.tool_call_id,
    )

    messages = [last_ai_message, transfer_message] if last_ai_message else [transfer_message]

    return Command(
        goto="agent",
        update={
            "active_agent": "supervisor",
            "messages": messages,
            "topic_context": {},  # Clear context
        },
        graph=Command.PARENT,
    )
