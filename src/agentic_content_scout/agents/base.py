"""Base classes for agents."""

from typing import Any

from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_model
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

from agentic_content_scout.utils import ToolActionsLogger
from agentic_content_scout.llm.openai import get_mini_model, get_smart_model
from agentic_content_scout.schemas import MultiAgentState


MAX_MESSAGES = 16


@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Trim messages to prevent context overflow.

    Keeps the last N messages to cap context size per LLM call.
    This prevents quadratic token growth in ReAct loops.
    """
    messages = state.get("messages", [])
    if len(messages) <= MAX_MESSAGES:
        return None  # No changes needed
    return {"messages": messages[-MAX_MESSAGES:]}


class HandoffAgent:
    """Base for agents in the handoff pattern.

    Subclasses should define:
    - name: str - agent identifier for routing
    - system_prompt: str - the agent's system prompt
    - tools: list - tools available to this agent
    - use_smart_model: bool - True for complex reasoning, False for simple routing
    """

    name: str
    system_prompt: str
    tools: list
    use_smart_model: bool = True  # Override to False for simple routing agents

    def __init__(self):
        self.logger = ToolActionsLogger()

    def invoke(self, state: MultiAgentState) -> dict:
        """Invoke this agent with the given state."""
        model = get_smart_model() if self.use_smart_model else get_mini_model()
        agent = create_agent(
            model=model,
            tools=self.tools,
            system_prompt=self.system_prompt,
            middleware=[trim_messages],
        )
        return agent.invoke(state, config={
            "callbacks": [self.logger],
            "run_name": self.name,  # Shows agent name in LangSmith traces
        })


class ReasoningAgent:
    """Base class for standalone agents that log their reasoning.

    Used for agents invoked directly (not via handoff pattern).
    Example: ContentScout invoked via /scout command.

    Subclasses should:
    1. Call super().__init__()
    2. Set self.agent in their __init__
    3. Use self._invoke(task) instead of self.agent.invoke(...)
    """

    def __init__(self):
        self.logger = ToolActionsLogger()
        self.agent = None

    def _invoke(self, task: str) -> dict:
        """Invoke the agent with reasoning logger attached."""
        return self.agent.invoke(
            {"messages": [HumanMessage(content=task)]},
            config={"callbacks": [self.logger]},
        )
