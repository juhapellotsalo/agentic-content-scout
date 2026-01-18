# Agentic Content Scout

A personalized content aggregator and recommendation system built with LangGraph. Not just bookmarks - a knowledge base with intelligence that the user actively shapes.

## Quick Start

```bash
# Install dependencies
pip install -e .

# Set environment variables (copy from .env.example or create .env)
# Required: OPENAI_API_KEY, TAVILY_API_KEY
# Optional: LANGSMITH_API_KEY (for tracing)

# Run the CLI
scout
# or
python -m agentic_content_scout
```

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: LangChain 1.0 + LangGraph 1.0
- **LLM**: OpenAI (gpt-5-mini, gpt-5.2 via `llm/openai.py`)
- **Search**: Tavily API
- **CLI**: prompt_toolkit (full-screen TUI)
- **Persistence**: MemorySaver (conversation), YAML (curated links)
- **Observability**: LangSmith + local `logs/tool-actions.log`

## Core Concept

The system tracks topics of interest (e.g., "agentic coding tools", "video game industry") and autonomously scans the web to surface relevant content. Unlike traditional recommendation systems driven by opaque algorithms, this one is user-tailored through natural language commands.

## Architecture

Two operational modes sharing persistent state:

| Mode | Trigger | Purpose |
|------|---------|---------|
| **Interactive** | CLI input | Converse, manage topics, adjust preferences |
| **Autonomous** | `/scout` command | Search, filter, curate content for a topic |

### Handoff Pattern (Current)

```
+-----------------------------------------------------------+
|                    CLI (cli/app.py)                       |
|  * Full-screen TUI with prompt_toolkit                    |
|  * Slash commands: /topics, /help, /exit                  |
|  * Animated spinner, input history, topic cycling         |
+---------------------------+-------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|               Orchestrator (core/graph.py)                |
|  * Unified StateGraph with dynamic agent routing          |
|  * Checkpointed memory (MemorySaver)                      |
|  * Interrupt handling for HITL                            |
+---------------------------+-------------------------------+
                            |
                            v
                  +-------------------+
                  |   active_agent    |
                  |   state field     |
                  +---------+---------+
         +-----------------+------------------+
         v                 v                  v
   +-------------+   +-------------+   +-------------+
   | Supervisor  |   |   Topic     |   |  Content    |
   |  (router)   |   |  Manager    |   |   Scout     |
   +-------------+   +-------------+   +-------------+
```

The handoff pattern uses a single graph with `active_agent` state that dynamically routes to agents:
- Supervisor hands off to TopicManager via `handoff_to_topics` tool
- Supervisor hands off to ContentScout via `handoff_to_scout` tool
- TopicManager hands back via `handoff_to_supervisor` tool
- Each agent owns its conversation until handoff

## Agents

### Supervisor (Router)
- **Role**: Intent classification and delegation
- **Base**: Extends `HandoffAgent`
- **Tools**:
  - `reflect` - Pause to think before acting
  - `handoff_to_topics` - Hand off to TopicManager
  - `handoff_to_scout` - Hand off to ContentScout

### TopicManager
- **Role**: Topic CRUD with adaptive HITL
- **Base**: Extends `HandoffAgent`
- **HITL**: Uses `gather_preferences` with `interrupt()` for user input
- **Tools**:
  - `reflect` - Think through the task
  - `gather_preferences` - Ask user questions (triggers interrupt)
  - `list_topics` - Get all topic slugs
  - `create_topic` - Create with preferences content
  - `get_topic` - Read topic preferences
  - `update_topic` - Rewrite preferences
  - `rename_topic` - Rename topic (slugifies new name)
  - `delete_topic` - Remove topic
  - `handoff_to_supervisor` - Hand back when done

### ContentScout
- **Role**: Content discovery and curation for a topic
- **Trigger**: Via `handoff_to_scout` or `/scout <topic>` CLI command
- **Pattern**: Subgraph with focused ReAct loop
- **Nodes**: `resolve_topic` -> `load_context` -> `search_evaluate` -> `save_articles`
- **Context**: Receives topic preferences + existing URLs
- **Persistence**: Saves curated articles to `topics/{slug}/links.yaml`
- **Deduplication**: Loads existing URLs and instructs agent to skip them
- **Tools**:
  - `tavily_search` - Web search via Tavily API

## Tool Actions Log

All agents attach a `ToolActionsLogger` callback. This logs tool calls and results to `logs/tool-actions.log` for debugging:

```
Session: 2024-01-15 10:30:00
----------------------------------------
[tavily_search]
{'queries': ['metroidvania 2025 releases']}
-> [{"title": "Best Metroidvanias...", "url": "https://..."}]

[Response]
{"articles": [...], "summary": "Found a PC Gamer feature..."}
```

Tail the log in a separate terminal: `tail -f logs/tool-actions.log`

## Prompt Design Patterns

### Keep Prompts Slim

| Agent Type | Target Length | Focus |
|------------|---------------|-------|
| Router (Supervisor) | 150-200 tokens | Intent classification + brief responses |
| Executor (TopicManager) | 200-300 tokens | Workflow + constraints |

### Decomposition Strategy

1. **System prompt**: Role and decision-making
2. **Tool docstrings**: Operational details (LLM sees these!)
3. **Agent prompts**: Format and execution rules

## Design Patterns

| Pattern | Purpose | Implementation |
|---------|---------|----------------|
| **Handoff Pattern** | Multi-turn agent conversations | `active_agent` state + `Command(goto=...)` |
| **HandoffAgent Base** | Agents in handoff graph | Encapsulates prompt + tools |
| **Subgraph Pattern** | ContentScout workflow | StateGraph with focused nodes |
| **HITL via interrupt()** | User input during agent flow | `gather_preferences` tool |
| **Message Trimming** | Prevent context overflow | `trim_messages` middleware (MAX_MESSAGES=16) |
| **Orchestrator** | Graph execution | Separate from agent logic |

## Topic System

File-based preference storage. Compact enough to inject into agent prompts.

### Structure

```
topics/
  default_preferences.md      # global preferences (manual edit only)
  agentic-ai-patterns/
    preferences.md            # topic-specific preferences
    links.yaml                # curated articles (appended by ContentScout)
  metroidvania-games/
    preferences.md
    links.yaml
```

### Preferences Template

```markdown
# Topic Name

## Focus
Brief description of what this topic covers

## Sources
- Prefer: github.com, arxiv.org
- Avoid: forbes.com, venturebeat.com

## Guidance
- Technical depth over news coverage
- Skip: funding announcements, listicles, marketing fluff
```

### Links Storage (links.yaml)

```yaml
- title: "Article Title"
  url: "https://example.com/article"
  reason: "Why this was selected"
  date: "2024-01-15"
```

## Control Flows

### Interactive Flow (CLI)
```
User Input -> Orchestrator -> agent_node(active_agent) -> Response or Interrupt
                 |
                 +-- Checkpointed memory (MemorySaver)

Handoff: Supervisor -> TopicManager -> ... -> Supervisor
HITL: gather_preferences -> interrupt() -> CLI shows question -> resume
```

Example interactions:
- "Create a topic for AI safety" -> Supervisor -> handoff -> TopicManager (may HITL)
- "What topics do I have?" -> Supervisor -> handoff -> TopicManager -> list
- "What's RLHF?" -> Supervisor (direct response, no handoff)

### Scout Flow
```
handoff_to_scout -> ContentScout.invoke() -> Subgraph:
                                              resolve_topic (LLM + optional HITL)
                                              -> load_context (no LLM)
                                              -> search_evaluate (ReAct loop)
                                              -> save_articles (no LLM)
                                           -> Return summary to Supervisor
```

## Project Structure

```
agentic-content-scout/
+-- pyproject.toml              # Package config, dependencies, entry point
+-- logs/
|   +-- tool-actions.log        # Agent tool calls trace
+-- topics/
|   +-- default_preferences.md
|   +-- {topic-slug}/
|       +-- preferences.md
|       +-- links.yaml
+-- scripts/
|   +-- trace.py                # LangSmith trace viewer
|   +-- test_content_scout.py   # Node-level testing script
+-- src/
    +-- agentic_content_scout/
        +-- __init__.py
        +-- __main__.py         # Entry point for python -m
        +-- cli/
        |   +-- __init__.py     # Exports main, topic_state
        |   +-- app.py          # Full-screen TUI application
        |   +-- commands.py     # Slash command handlers
        |   +-- state.py        # TopicState for topic cycling
        +-- core/
        |   +-- __init__.py
        |   +-- graph.py        # Orchestrator + graph building
        +-- utils/
        |   +-- __init__.py
        |   +-- briefs.py       # load_brief, save_brief
        |   +-- logging.py      # ToolActionsLogger
        |   +-- preferences.py  # load_preferences
        +-- schemas/
        |   +-- __init__.py
        |   +-- models.py       # MultiAgentState, ScoutState, CurationOutput
        +-- llm/
        |   +-- __init__.py
        |   +-- openai.py       # get_mini_model, get_smart_model
        +-- tools/
        |   +-- __init__.py     # Exports all tools
        |   +-- handoff_tools.py    # handoff_to_topics, handoff_to_scout, handoff_to_supervisor
        |   +-- tavily_tools.py     # tavily_search
        |   +-- thinking_tools.py   # reflect
        |   +-- topic_tools.py      # CRUD tools + gather_preferences
        |   +-- content_tools.py    # save_article, get_saved_urls
        +-- agents/
            +-- __init__.py
            +-- base.py             # HandoffAgent, ReasoningAgent, trim_messages
            +-- supervisor.py       # Supervisor (router agent)
            +-- topic_manager.py    # TopicManager
            +-- content_scout.py    # ContentScout subgraph
```

## Development

### Prerequisites
- Python 3.11+
- OpenAI API key
- Tavily API key
- (Optional) LangSmith API key for tracing

### Environment Variables

Create a `.env` file with:
```
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
LANGSMITH_API_KEY=ls-...        # Optional
LANGCHAIN_TRACING_V2=true       # Optional - enable LangSmith tracing
LANGCHAIN_PROJECT=agentic-content-scout  # Optional
```

### Commands

| Command | Description |
|---------|-------------|
| `pip install -e .` | Install package in editable mode |
| `scout` | Run the CLI (entry point from pyproject.toml) |
| `python -m agentic_content_scout` | Alternative way to run CLI |
| `python scripts/trace.py` | View LangSmith trace summaries |
| `python scripts/trace.py -n 5 -v` | View 5 traces with verbose output |
| `python scripts/test_content_scout.py full` | Test ContentScout end-to-end |
| `python scripts/test_content_scout.py search_evaluate` | Test search node only |
| `tail -f logs/tool-actions.log` | Watch agent tool calls in real-time |

### CLI Commands

| Command | Description |
|---------|-------------|
| `/topics` | List all tracked topics |
| `/help` | Show available commands |
| `/exit` | Exit the CLI |
| `Ctrl+C` or `Ctrl+D` | Exit the CLI |
| `Shift+Tab` | Cycle through topics |
| `Up/Down` | Navigate input history or command menu |

## Code Conventions

- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Imports**: Absolute imports from `agentic_content_scout.*`
- **Tools**: Use `@tool` decorator, include docstring with Args section
- **Agents**: Extend `HandoffAgent` or implement as subgraph
- **State**: Use TypedDict with `NotRequired` for optional fields

## Testing

Currently no formal test suite. Manual testing via:
- `scripts/test_content_scout.py` - Node-level testing for ContentScout
- `logs/tool-actions.log` - Observe tool calls and responses
- LangSmith traces for end-to-end debugging

## Key Files

| File | Purpose |
|------|---------|
| `core/graph.py` | Orchestrator, agent_node, build_graph |
| `agents/base.py` | HandoffAgent, ReasoningAgent, trim_messages middleware |
| `agents/content_scout.py` | ContentScout subgraph with 4 nodes |
| `cli/app.py` | Full-screen TUI with prompt_toolkit |
| `tools/handoff_tools.py` | Command-based handoff between agents |
| `schemas/models.py` | MultiAgentState, ScoutState for graph state |

## Claude Code Subagents

Custom subagent definitions in `.claude/agents/`:

### LangGraph Docs Search

**File**: `.claude/agents/langgraph-docs.md`

Context-efficient pattern for searching LangGraph/LangChain documentation. Isolates verbose MCP results into a subagent context, returns synthesized answers.

**Usage**:
```python
Task(
  subagent_type="general-purpose",
  description="Search LangGraph docs",
  prompt="""Search LangGraph docs using mcp__langchain-docs__SearchDocsByLangChain.

  Question: How do I implement the handoff pattern?

  Return under 500 words with essential code snippets."""
)
```

**Why**: Direct MCP searches return ~5000 tokens of raw docs. Subagent pattern returns ~400 tokens of synthesized answer. ~10x context savings.

## Known Issues

- **No tests**: Formal test suite not yet created - using scripts and logs for manual testing
