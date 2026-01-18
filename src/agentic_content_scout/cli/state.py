"""CLI state management - single source of truth for selected topic."""

from agentic_content_scout.tools import get_topic_slugs


class TopicState:
    """Manages the currently selected topic."""

    def __init__(self):
        self._topics: list[str] = []
        self._index: int = -1  # -1 means no topic selected
        self.refresh_topics()

    def refresh_topics(self) -> None:
        """Reload available topics from disk."""
        self._topics = get_topic_slugs()

    @property
    def topics(self) -> list[str]:
        """All available topics."""
        return self._topics

    @property
    def selected(self) -> str | None:
        """Currently selected topic, or None if none selected."""
        if self._index >= 0 and self._index < len(self._topics):
            return self._topics[self._index]
        return None

    @selected.setter
    def selected(self, topic: str | None) -> None:
        """Set the selected topic by name."""
        if topic is None:
            self._index = -1
        elif topic in self._topics:
            self._index = self._topics.index(topic)
        else:
            # Topic not in list - refresh and try again
            self.refresh_topics()
            if topic in self._topics:
                self._index = self._topics.index(topic)

    def cycle(self) -> str | None:
        """Cycle to next topic (including 'none'). Returns the newly selected topic."""
        if not self._topics:
            self.refresh_topics()
        if not self._topics:
            return None

        # Cycle: -1 (none) → 0 → 1 → ... → len-1 → -1 (none)
        self._index += 1
        if self._index >= len(self._topics):
            self._index = -1  # Back to no selection
        return self.selected

    def has_topics(self) -> bool:
        """Check if any topics are available."""
        return len(self._topics) > 0


# Global state instance
topic_state = TopicState()
