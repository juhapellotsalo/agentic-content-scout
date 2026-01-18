"""Main CLI application - Full-screen TUI like Claude Code."""

import asyncio
import os
import threading
import time

from dotenv import load_dotenv

load_dotenv()  # Must run before LangChain imports

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    FormattedTextControl,
    HSplit,
    Layout,
    Window,
)
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.styles import Style

from agentic_content_scout.core import Orchestrator

from .commands import COMMANDS, handle_command
from .state import topic_state

# Colors
CYAN = "#36b5b5"
DIM = "#666666"
WHITE = "#ffffff"

# Style
STYLE = Style.from_dict({
    "header": CYAN,
    "header-dim": DIM,
    "separator": DIM,
    "user-msg": "#bbbbbb bg:#2a2a2a",
    "ai-msg": WHITE,
    "thinking": "#994444",
    "topic": CYAN,
    "hint": DIM,
    "prompt": DIM,
    # Slash command list
    "cmd-name": DIM,
    "cmd-desc": DIM,
    "cmd-selected": CYAN,
    "cmd-desc-selected": DIM,
})

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class SlashCommandCompleter(Completer):
    """Completer for slash commands."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        partial = text[1:].lower()
        for name, cmd in COMMANDS.items():
            if name.startswith(partial):
                yield Completion(
                    f"/{name}",
                    start_position=-len(text),
                    display=f"/{name}",
                    display_meta=cmd.description,
                )


class ContentScoutApp:
    """Full-screen CLI application."""

    def __init__(self):
        self.orchestrator = Orchestrator()
        self.messages: list[tuple[str, str]] = []  # (role, content)
        self.thinking = False
        self.spinner_frame = 0
        self.spinner_thread = None

        # Slash command selection state
        self.command_index = 0
        self.command_list = list(COMMANDS.keys())

        # Input history
        self.history: list[str] = []
        self.history_index = 0

        # Key bindings
        self.bindings = KeyBindings()

        @self.bindings.add("c-c")
        @self.bindings.add("c-d")
        def exit_(event):
            self._stop_spinner()
            event.app.exit()

        @self.bindings.add("enter")
        def submit_(event):
            if not self.thinking:
                self._handle_input(event)

        @self.bindings.add("s-tab")
        def cycle_topic_(event):
            if not self._in_slash_mode():
                topic_state.cycle()
                event.app.invalidate()

        @self.bindings.add("up")
        def cmd_up_(event):
            if self._in_slash_mode():
                self.command_index = (self.command_index - 1) % len(self.command_list)
                event.app.invalidate()
            elif self.history:
                # Cycle backward through history
                if self.history_index > 0:
                    self.history_index -= 1
                    self.input_buffer.text = self.history[self.history_index]
                    self.input_buffer.cursor_position = len(self.input_buffer.text)

        @self.bindings.add("down")
        def cmd_down_(event):
            if self._in_slash_mode():
                self.command_index = (self.command_index + 1) % len(self.command_list)
                event.app.invalidate()
            elif self.history:
                # Cycle forward through history
                if self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    self.input_buffer.text = self.history[self.history_index]
                    self.input_buffer.cursor_position = len(self.input_buffer.text)
                elif self.history_index == len(self.history) - 1:
                    # Past end - clear input
                    self.history_index = len(self.history)
                    self.input_buffer.text = ""

        # Input buffer with text change callback
        self.input_buffer = Buffer(
            multiline=False,
            on_text_changed=lambda _: self._on_input_changed(),
        )

        # Build layout
        self.layout = self._create_layout()

        # Application
        self.app = Application(
            layout=self.layout,
            key_bindings=self.bindings,
            style=STYLE,
            full_screen=True,
            mouse_support=True,
        )

    def _get_separator(self) -> str:
        try:
            width = os.get_terminal_size().columns
        except OSError:
            width = 80
        return "─" * width

    def _create_layout(self) -> Layout:
        header = Window(
            FormattedTextControl(self._get_header),
            height=3,
        )

        history = Window(
            FormattedTextControl(self._get_history),
            wrap_lines=True,
            dont_extend_height=True,  # Only take space needed
        )

        top_sep = Window(
            FormattedTextControl(lambda: [("class:separator", self._get_separator())]),
            height=1,
        )

        input_area = Window(
            BufferControl(
                buffer=self.input_buffer,
                input_processors=[],
            ),
            height=1,
            get_line_prefix=lambda line, wrap: [("class:prompt", "› ")],
        )

        bottom_sep = Window(
            FormattedTextControl(lambda: [("class:separator", self._get_separator())]),
            height=1,
        )

        status_bar = Window(
            FormattedTextControl(self._get_status),
            dont_extend_height=True,  # Dynamic height based on content
        )

        # Empty filler takes remaining space at bottom
        filler = Window()

        return Layout(
            HSplit([
                header,
                history,
                top_sep,
                input_area,
                bottom_sep,
                status_bar,
                filler,  # Pushes everything up
            ]),
            focused_element=input_area,
        )

    def _get_header(self) -> list:
        return [
            ("class:header", "Content Scout CLI\n"),
            ("class:header-dim", "Type /help for commands, /exit to quit\n"),
        ]

    def _get_history(self) -> list:
        result = []
        for role, content in self.messages:
            if role == "user":
                result.append(("class:user-msg", f" {content} "))
                result.append(("", "\n\n"))
            else:
                result.append(("class:ai-msg", f"● {content}"))
                result.append(("", "\n\n"))

        # Show thinking spinner if waiting for response
        if self.thinking:
            frame = SPINNER_FRAMES[self.spinner_frame % len(SPINNER_FRAMES)]
            result.append(("class:thinking", f"{frame} Thinking..."))
            result.append(("", "\n"))

        return result

    def _on_input_changed(self):
        """Called when input text changes."""
        # Reset command index when text changes
        self.command_index = 0
        # Refresh UI to update command list
        if hasattr(self, 'app'):
            self.app.invalidate()

    def _in_slash_mode(self) -> bool:
        """Check if input starts with / (slash command mode)."""
        text = self.input_buffer.text
        return text.startswith("/") and " " not in text

    def _get_status(self) -> list:
        # Slash command mode - show command list
        if self._in_slash_mode():
            result = []
            partial = self.input_buffer.text[1:].lower()  # Text after /

            # Filter commands matching partial input
            matching = [cmd for cmd in self.command_list if cmd.startswith(partial)]
            if not matching:
                matching = self.command_list  # Show all if no match

            # Ensure index is valid
            if self.command_index >= len(matching):
                self.command_index = 0

            for i, cmd_name in enumerate(matching):
                cmd = COMMANDS[cmd_name]
                if i == self.command_index:
                    # Highlighted
                    result.append(("class:cmd-selected", f"/{cmd_name:<18}"))
                    result.append(("class:cmd-desc-selected", f" {cmd.description}"))
                else:
                    result.append(("class:cmd-name", f"/{cmd_name:<18}"))
                    result.append(("class:cmd-desc", f" {cmd.description}"))
                result.append(("", "\n"))

            return result

        # Normal mode - show topic selector
        if topic_state.selected:
            return [
                ("class:topic", topic_state.selected),
                ("class:hint", " (shift+tab to cycle)"),
            ]
        elif topic_state.has_topics():
            return [("class:hint", "shift+tab to select topic")]
        return []

    def _start_spinner(self):
        """Start the animated spinner."""
        self.thinking = True
        self.spinner_frame = 0

        def animate():
            while self.thinking:
                time.sleep(0.1)
                self.spinner_frame += 1
                # Schedule UI update on main thread
                self.app.invalidate()

        self.spinner_thread = threading.Thread(target=animate, daemon=True)
        self.spinner_thread.start()

    def _stop_spinner(self):
        """Stop the spinner."""
        self.thinking = False
        if self.spinner_thread:
            self.spinner_thread.join(timeout=0.2)
            self.spinner_thread = None

    def _handle_input(self, event):
        text = self.input_buffer.text.strip()

        # Add to history if not empty
        if text and (not self.history or self.history[-1] != text):
            self.history.append(text)
        self.history_index = len(self.history)

        # In slash mode, execute the selected command
        if self._in_slash_mode():
            partial = text[1:].lower()
            matching = [cmd for cmd in self.command_list if cmd.startswith(partial)]
            if not matching:
                matching = self.command_list

            if self.command_index < len(matching):
                selected_cmd = matching[self.command_index]
                self.input_buffer.reset()
                self.command_index = 0

                output, should_exit = handle_command(selected_cmd, [])
                if should_exit:
                    event.app.exit()
                    return
                if output:
                    self.messages.append(("ai", output))
                event.app.invalidate()
                return

        self.input_buffer.reset()

        if not text:
            return

        # Handle slash commands with args (e.g., "/scout topic-name")
        if text.startswith("/"):
            parts = text[1:].split()
            cmd = parts[0].lower()
            args = parts[1:]

            output, should_exit = handle_command(cmd, args)
            if should_exit:
                event.app.exit()
                return
            if output:
                self.messages.append(("ai", output))
            event.app.invalidate()
            return

        # Add user message immediately
        self.messages.append(("user", text))
        event.app.invalidate()

        # Start spinner and fetch response in background
        self._start_spinner()

        def fetch_response():
            try:
                result = self.orchestrator.chat(text)
                response = result.get("question") if result.get("interrupt") else result.get("response", "")
            except Exception as e:
                response = f"Error: {e}"
            finally:
                self._stop_spinner()

            # Add response to messages
            self.messages.append(("ai", response))
            self.app.invalidate()

        thread = threading.Thread(target=fetch_response, daemon=True)
        thread.start()

    def run(self):
        """Run the application."""
        self.app.run()


def main():
    """Entry point."""
    app = ContentScoutApp()
    app.run()
