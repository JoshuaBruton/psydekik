"""Grounded session state for Chappie."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ChappieSessionState:
    """Small authoritative memory for the current Chappie session."""

    assistant_name: str = "Chappie"
    user_name: str = "Josh"
    platform_name: str = "Psydekik"

    previous_user_message: str | None = None
    last_user_message: str | None = None
    last_assistant_message: str | None = None

    last_system_intent: str | None = None
    last_system_status: dict[str, Any] | None = field(
        default=None
    )

    def record_user_message(
        self,
        message: str,
    ) -> None:
        """Record a new user turn while preserving the previous one."""

        message = message.strip()

        if not message:
            return

        self.previous_user_message = (
            self.last_user_message
        )
        self.last_user_message = message

    def record_assistant_message(
        self,
        message: str,
    ) -> None:
        """Record Chappie's most recent spoken/display response."""

        message = message.strip()

        if message:
            self.last_assistant_message = message

    def remember_system_result(
        self,
        intent: str,
        status: dict[str, Any],
    ) -> None:
        """Remember the latest authoritative system result."""

        self.last_system_intent = intent
        self.last_system_status = status
