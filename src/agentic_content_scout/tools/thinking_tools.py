"""
Thinking tool for agent reflection and decision-making.
"""

from langchain_core.tools import tool


@tool(parse_docstring=True)
def reflect(thought: str) -> str:
    """Pause to reflect on progress and plan next steps.

    Use this to analyze what you've found, identify gaps, and decide whether
    to continue or move to the next phase of your workflow.

    Args:
        thought: Your analysis and decision on next steps

    Returns:
        Confirmation that reflection was recorded
    """
    return f"Recorded: {thought}"
