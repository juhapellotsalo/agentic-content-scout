"""Graph orchestrator - builds and runs the unified agent graph."""

from typing import Literal

from langchain.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END

from agentic_content_scout.utils import ToolActionsLogger
from agentic_content_scout.schemas import MultiAgentState


def _get_agents():
    """Lazy import agents to avoid circular imports."""
    from agentic_content_scout.agents import ContentScout, Supervisor, TopicManager
    return {
        "supervisor": Supervisor(),
        "topic_manager": TopicManager(),
        "content_scout": ContentScout(),
    }


# Lazy-initialized agent registry
_agents = None


def get_agents():
    """Get the agent registry, initializing if needed."""
    global _agents
    if _agents is None:
        _agents = _get_agents()
    return _agents


def agent_node(state: MultiAgentState) -> dict:
    """Dynamic agent node that routes based on active_agent."""
    active_agent = state.get("active_agent", "supervisor")
    agents = get_agents()
    return agents[active_agent].invoke(state)


def should_continue(state: MultiAgentState) -> Literal["agent", "__end__"]:
    """Determine if we should continue or end."""
    messages = state.get("messages", [])
    if not messages:
        return "__end__"

    last_message = messages[-1]

    # If last message is AI with no tool calls, we're done
    if isinstance(last_message, AIMessage) and not last_message.tool_calls:
        return "__end__"

    # Otherwise continue (tool calls pending or handoff occurred)
    return "agent"


def build_graph() -> StateGraph:
    """Build the unified agent graph."""
    builder = StateGraph(MultiAgentState)

    builder.add_node("agent", agent_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, ["agent", END])

    return builder


class Orchestrator:
    """Runs the agent graph with conversation memory and interrupt handling."""

    def __init__(self, thread_id: str = "default"):
        self.thread_id = thread_id
        self.checkpointer = MemorySaver()
        self.logger = ToolActionsLogger()
        self.graph = build_graph().compile(checkpointer=self.checkpointer)
        self._interrupted = False

    def chat(self, message: str) -> dict:
        """Send a message and get a response.

        Args:
            message: User's message

        Returns:
            Dict with 'response' and 'path', or 'interrupt' and 'question' for HITL
        """
        from langchain_core.messages import HumanMessage

        config = {
            "configurable": {"thread_id": self.thread_id},
            "callbacks": [self.logger],
        }

        # Check if we're resuming from an interrupt
        if self._interrupted:
            from langgraph.types import Command

            result = self.graph.invoke(Command(resume=message), config=config)
            self._interrupted = False
        else:
            result = self.graph.invoke(
                {"messages": [HumanMessage(content=message)]},
                config=config,
            )

        # Check for interrupt
        if "__interrupt__" in result:
            self._interrupted = True
            interrupt_value = result["__interrupt__"][0].value
            return {"interrupt": True, "question": interrupt_value.get("question", str(interrupt_value))}

        # Return last AI message
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return {"response": msg.content}

        return {"response": "No response generated."}
