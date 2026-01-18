import os

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel


def get_mini_model() -> BaseChatModel:
    """Fast, cheap model for token-heavy tasks (search loops, evaluation)."""
    model = os.environ.get("MINI_MODEL", "openai:gpt-5-mini")
    return init_chat_model(model=model)


def get_smart_model() -> BaseChatModel:
    """Reasoning model for understanding intent and making decisions."""
    model = os.environ.get("SMART_MODEL", "openai:gpt-5.2")
    return init_chat_model(model=model)