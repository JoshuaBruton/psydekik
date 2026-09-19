"""Chappie's visual presence card for the native console."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from typing import Any, Callable

import bootstack as bs

from frontend_console.state.chappie_state import ChappieSnapshot


ASSET_PATH = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "chappie.png"
)


class ChappiePresenceCard:
    """Render Chappie's avatar, activity, and talk control."""

    def __init__(self) -> None:
        self._on_talk: Callable[[], None] | None = None
        self.avatar_image = self._load_avatar()

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
                bs.Label(
                    image=self.avatar_image,
                    anchor="center",
                )

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
        self.mode_label.text = f"{snapshot.mode.value} · Voice online"
        self.detail_label.text = snapshot.detail
        self.transcript_label.text = (
            f'You: “{snapshot.transcript}”'
            if snapshot.transcript
            else ""
        )

    def _request_talk(self) -> None:
        if self._on_talk is not None:
            self._on_talk()

    @staticmethod
    def _load_avatar() -> tk.PhotoImage:
        if not ASSET_PATH.is_file():
            raise FileNotFoundError(
                f"Chappie avatar not found: {ASSET_PATH}"
            )

        # The source is 1230x1278. Tk performs a lossless integer
        # subsample here, producing a dashboard-friendly ~246x256 image.
        return tk.PhotoImage(file=str(ASSET_PATH)).subsample(5, 5)
