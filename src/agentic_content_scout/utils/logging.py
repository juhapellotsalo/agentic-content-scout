"""Logging utilities for debugging agents."""

from datetime import datetime
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler

LOGS_DIR = Path(__file__).parent.parent.parent.parent / "logs"


class ToolActionsLogger(BaseCallbackHandler):
    """Log agent tool actions to file for debugging.

    Usage:
        tail -f logs/tool-actions.log
    """

    _session_started = False

    def __init__(self):
        LOGS_DIR.mkdir(exist_ok=True)
        self.log_file = LOGS_DIR / "tool-actions.log"
        # Only clear log once per process (first logger instance)
        if not ToolActionsLogger._session_started:
            ToolActionsLogger._session_started = True
            with open(self.log_file, "w") as f:
                f.write(f"Session: {datetime.now()}\n{'─'*40}\n")

    def _write(self, text: str):
        with open(self.log_file, "a") as f:
            f.write(text)

    def on_llm_end(self, response, **kwargs):
        text = response.generations[0][0].text if response.generations else ""
        if text:
            self._write(f"\n[Response]\n{text}\n")

    def on_tool_start(self, serialized, input_str, **kwargs):
        name = serialized.get("name", "unknown")
        self._write(f"\n[{name}]\n{input_str}\n")

    def on_tool_end(self, output, **kwargs):
        text = str(output)
        out = f"{text[:300]}..." if len(text) > 300 else text
        self._write(f"→ {out}\n")