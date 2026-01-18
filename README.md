Agentic Content Scout
=====================

A personalized content aggregator built with LangGraph 1.0. Tracks topics of
interest and searches the web to surface relevant articles.

This project experiments with:
- Orchestrator/supervisor pattern for multi-agent routing
- Conversational CLI with full-screen TUI
- Agent handoffs using LangGraph's Command(goto=...) pattern
- Human-in-the-loop via interrupt() for gathering preferences

All agents use LangGraph's create_agent() with tool binding and middleware.
The HandoffAgent base class wraps create_agent() with message trimming and
selective model usage (cheap models for routing, reasoning models for decisions).


Architecture
------------

```
User Input
    │
    ▼
┌─────────────────────────────────────────┐
│           Orchestrator                   │
│  (StateGraph with checkpointed memory)  │
└─────────────────┬───────────────────────┘
                  │
                  ▼
         ┌───────────────┐
         │ active_agent  │
         └───────┬───────┘
    ┌────────────┼────────────┐
    ▼            ▼            ▼
┌────────┐ ┌───────────┐ ┌─────────────┐
│Supervisor│ │TopicManager│ │ContentScout│
│ (Mini)  │ │  (Smart)   │ │  (Mini)    │
└────────┘ └───────────┘ └─────────────┘
```

| Agent | Model | Role |
|-------|-------|------|
| Supervisor | Mini | Routes requests, classifies intent |
| TopicManager | Smart | CRUD for topics, uses HITL to gather preferences |
| ContentScout | Mini | Searches web via Tavily, evaluates and saves articles |


Key Patterns
------------

**Handoff**: Agents transfer control via tool calls that update `active_agent` state:
```python
@tool
def handoff_to_topics(task: str) -> Command:
    return Command(goto="agent", update={"active_agent": "topic_manager"})
```

**HITL via interrupt()**: Pause execution to gather user input:
```python
@tool
def gather_preferences(question: str) -> str:
    response = interrupt({"question": question})
    return response
```

**Selective Model Usage**: Smart models for reasoning, mini models for routing:
```python
class HandoffAgent:
    use_smart_model: bool = True  # Override per agent

    def invoke(self, state):
        model = get_smart_model() if self.use_smart_model else get_mini_model()
```


What I Learned
--------------

### Token Economics

A simple query like "What links do I have?" consumed 4,295 tokens across 4 LLM calls:
- System prompts repeat with every call (~1,200 tokens overhead)
- Message history accumulates within agent sessions
- Handoff round-trips add overhead (Supervisor→Agent→Supervisor)

The handoff pattern trades tokens for architectural clarity. For read-only queries,
direct responses would be more efficient.

### Model Selection

Not every agent needs a reasoning model:
- **Routing** (Supervisor): Simple classification → Mini model
- **Ambiguous requests** (TopicManager): Needs reasoning → Smart model
- **Search loops** (ContentScout): Token-heavy, constrained → Mini model


Setup
-----

1. Install:

    pip install -e .

2. Create .env (see .env.example):

    OPENAI_API_KEY=sk-...
    TAVILY_API_KEY=tvly-...

3. Run:

    scout

    Or: python -m agentic_content_scout


CLI Commands
------------

| Command | Description |
|---------|-------------|
| /topics | List tracked topics |
| /help | Show commands |
| /exit | Exit |
| Shift+Tab | Cycle through topics |

Natural language for everything else.


Future Optimizations (Not Implemented)
--------------------------------------

- Direct returns for read-only queries (skip final Supervisor call)
- Parallel tool calling where dependencies allow
- Tool result summarization to reduce context growth
- Streaming responses for better UX


License
-------

MIT
