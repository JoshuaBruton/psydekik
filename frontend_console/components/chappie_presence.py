"""Chappie's visual presence card for the native console."""

from __future__ import annotations

from typing import Any, Callable

import bootstack as bs

from frontend_console.components.chappie_avater import ChappieAvatar
from frontend_console.state.chappie_state import (
    ChappieMode,
    ChappieSnapshot,
)


class ChappiePresenceCard:
    """Render Chappie's avatar, activity, and talk control."""

    def __init__(self, scheduler: Any) -> None:
        self._on_talk: Callable[[], None] | None = None

        self.avatar = ChappieAvatar(
            scheduler,
            display_width=260,
        )

        with bs.Card(
            padding=20,
            gap=12,
            grow_items=True,
            horizontal_items="stretch",
            accent="primary",
        ):
            with bs.Row(
                gap=20,
                grow_items=True,
                weights=[1, 2],
                vertical_items="center",
            ):
                self.avatar_label: Any = bs.Label(
                    image=self.avatar.image,
                    anchor="center",
                )

                self.avatar.attach(self.avatar_label)

                with bs.Column(
                    gap=10,
                    horizontal_items="stretch",
                    vertical_items="center",
                ):
                    bs.Label(
                        "CHAPPIE",
                        icon="stars",
                        accent="muted",
                    )

                    self.headline_label: Any = bs.Label(
                        "Bringing Chappie online...",
                        font="heading-lg",
                        accent="primary",
                        wrap_width=520,
                    )

                    self.mode_label: Any = bs.Label(
                        "Starting · Voice initializing",
                        accent="warning",
                    )

                    self.detail_label: Any = bs.Label(
                        "Loading local speech and conversation services.",
                        accent="muted",
                        wrap_width=520,
                    )

                    self.transcript_label: Any = bs.Label(
                        "",
                        wrap_width=520,
                    )

                    self.talk_button: Any = bs.Button(
                        "Talk to Chappie",
                        icon="mic-fill",
                        accent="primary",
                        on_click=self._request_talk,
                    )

    def bind_talk(self, handler: Callable[[], None]) -> None:
        """Attach the controller after the page has been constructed."""
        self._on_talk = handler

    def render(self, snapshot: ChappieSnapshot) -> None:
        """Apply one state snapshot on Tk's main thread."""
        self.headline_label.text = snapshot.headline
        self.mode_label.text = (
            f"{snapshot.mode.value} · Voice online"
        )
        self.detail_label.text = snapshot.detail
        self.transcript_label.text = (
            f'You: “{snapshot.transcript}”'
            if snapshot.transcript
            else ""
        )

        if snapshot.mode in {
            ChappieMode.IDLE,
            ChappieMode.SLEEPING,
        }:
            self.avatar.start_idle()
        else:
            self.avatar.stop()

    def _request_talk(self) -> None:
        if self._on_talk is not None:
            self._on_talk()
