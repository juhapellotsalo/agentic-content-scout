# Agentic Content Scout

An exploration of CLI-driven conversational UI and multi-agent orchestration patterns using LangGraph.

## What This Project Explores

This project was built to learn and experiment with:

1. **CLI-driven Conversational UI** - Full-screen terminal interface using prompt_toolkit with animated spinners, input history, and topic cycling
2. **Orchestrator Pattern** - A central graph that routes between specialized agents
3. **Handoff Pattern** - Agents that transfer control to each other while maintaining conversation state
4. **Human-in-the-Loop (HITL)** - Using LangGraph's `interrupt()` for gathering user input mid-flow
5. **Model Selection Strategy** - Using expensive reasoning models where they matter, cheap models elsewhere

## Architecture

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

### Agents

| Agent | Model | Role |
|-------|-------|------|
| **Supervisor** | Mini | Routes requests, formats final responses |
| **TopicManager** | Smart | CRUD operations on topics, handles ambiguous queries |
| **ContentScout** | Mini | Searches web, evaluates and saves content |

### Key Patterns Implemented

**Handoff Pattern**: Agents transfer control via tool calls that update `active_agent` state:
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

**Selective Model Usage**: Smart models for reasoning, mini models for routing/searching:
```python
class HandoffAgent:
    use_smart_model: bool = True  # Override per agent

    def invoke(self, state):
        model = get_smart_model() if self.use_smart_model else get_mini_model()
```

## What I Learned

### Token Economics in Multi-Agent Systems

A simple query like "What links do I have?" consumed 4,295 tokens across 4 LLM calls:
- System prompts repeat with every call (~1,200 tokens overhead)
- Message history accumulates within agent sessions
- Handoff round-trips add overhead (Supervisor→Agent→Supervisor)

**Insight**: The handoff pattern trades tokens for architectural clarity. For read-only queries, direct responses would be more efficient.

### Model Selection Matters

Not every agent needs a reasoning model:
- **Routing** (Supervisor): Simple classification → Mini model works fine
- **Understanding ambiguous requests** (TopicManager): Needs reasoning → Smart model
- **Pattern matching** (resolve_topic): Trivial matching → Mini model
- **Search loops** (ContentScout): Token-heavy, constrained → Mini model

### LangSmith Tracing Tips

- Use `run_name` in config to identify agents in traces
- Direct tool calls outside graphs create orphan traces
- The parent trace contains the full flow; child traces are duplicates

## Running the Project

```bash
# Install
pip install -e .

# Configure (create .env)
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
MINI_MODEL=openai:gpt-4o-mini
SMART_MODEL=openai:gpt-4o
LANGSMITH_TRACING=true  # optional

# Run
scout
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `/topics` | List tracked topics |
| `/help` | Show commands |
| `/exit` | Exit |
| `Shift+Tab` | Cycle through topics |

## Project Structure

```
src/agentic_content_scout/
├── cli/
│   ├── app.py          # Full-screen TUI
│   ├── commands.py     # Slash commands
│   └── state.py        # Topic selection state
├── core/
│   └── graph.py        # Orchestrator + graph
├── agents/
│   ├── base.py         # HandoffAgent base class
│   ├── supervisor.py   # Router agent
│   ├── topic_manager.py# Topic CRUD
│   └── content_scout.py# Content discovery subgraph
├── tools/              # All agent tools
├── llm/
│   └── openai.py       # Model factories
└── schemas/
    └── models.py       # State definitions
```

## Key Files

| File | What It Demonstrates |
|------|---------------------|
| `core/graph.py` | Orchestrator pattern, dynamic agent routing |
| `agents/base.py` | Handoff base class, model selection, message trimming |
| `agents/content_scout.py` | Subgraph pattern, 4-node workflow |
| `tools/handoff_tools.py` | Command-based agent handoffs |
| `cli/app.py` | prompt_toolkit full-screen TUI |

## Future Optimizations (Not Implemented)

1. **Direct returns for read-only queries** - Skip final Supervisor call
2. **Parallel tool calling** - Where dependencies allow
3. **Tool result summarization** - Reduce context growth
4. **Streaming responses** - Better UX for long operations

## Tech Stack

- **LangGraph** - Agent orchestration and state management
- **LangChain** - LLM abstractions and tool definitions
- **prompt_toolkit** - Terminal UI
- **Tavily** - Web search
- **LangSmith** - Tracing and debugging

---

*This project prioritized learning over production-readiness. The patterns explored here—handoffs, HITL, selective model usage—are applicable to more complex agentic systems.*
