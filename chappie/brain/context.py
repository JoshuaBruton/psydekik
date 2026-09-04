"""Short-term conversation context for Chappie."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ConversationContext:
    """Maintain a bounded rolling conversation history."""

    max_messages: int = 12
    messages: list[dict[str, str]] = field(default_factory=list)

    def add_user(self, content: str) -> None:
        self._add("user", content)

    def add_assistant(self, content: str) -> None:
        self._add("assistant", content)

    def _add(self, role: str, content: str) -> None:
        content = content.strip()

        if not content:
            return

        self.messages.append(
            {
                "role": role,
                "content": content,
            }
        )

        self._trim()

    def _trim(self) -> None:
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def snapshot(self) -> list[dict[str, str]]:
        return [message.copy() for message in self.messages]

    def clear(self) -> None:
        self.messages.clear()
