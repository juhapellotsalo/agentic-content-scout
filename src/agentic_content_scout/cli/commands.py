"""Slash command handlers for the CLI."""

from dataclasses import dataclass
from typing import Callable

from agentic_content_scout.tools import get_topic_slugs


@dataclass
class Command:
    """A slash command with handler and description."""

    handler: Callable[[list[str]], str | None]
    description: str


def cmd_topics(args: list[str]) -> str | None:
    """List all topics."""
    topics = get_topic_slugs()
    if not topics:
        return "No topics found."
    return "Topics:\n" + "\n".join(f"- {t}" for t in topics)


def cmd_help(args: list[str]) -> str | None:
    """Show available commands."""
    lines = ["Available commands:"]
    for name, cmd in COMMANDS.items():
        lines.append(f"  /{name:<12} {cmd.description}")
    return "\n".join(lines)


# Command registry with descriptions
COMMANDS: dict[str, Command] = {
    "topics": Command(cmd_topics, "List all tracked topics"),
    "help": Command(cmd_help, "Show available commands"),
    "exit": Command(lambda _: None, "Exit the CLI"),
}

# Commands that trigger exit
EXIT_COMMANDS = {"exit"}


def handle_command(cmd: str, args: list[str]) -> tuple[str | None, bool]:
    """
    Handle a slash command.

    Returns:
        (output, should_exit) - output to print and whether to exit the REPL
    """
    if cmd in EXIT_COMMANDS:
        return None, True

    command = COMMANDS.get(cmd)
    if command:
        return command.handler(args), False

    return f"Unknown command: /{cmd}", False
