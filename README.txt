Agentic Content Scout
=====================

v. Tracks topics of
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

    User Input -> Orchestrator -> Supervisor -> [TopicManager | ContentScout]
                                     ^                    |
                                     +--------------------+
                                          (handoff back)

- Supervisor: Routes requests, classifies intent
- TopicManager: CRUD for topics, uses HITL to gather preferences
- ContentScout: Searches web via Tavily, evaluates and saves articles


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

/topics     List tracked topics
/help       Show commands
/exit       Exit

Shift+Tab cycles through topics. Natural language for everything else.


License
-------

MIT
