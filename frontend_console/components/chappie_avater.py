"""Animated visual avatar for Chappie's native console presence."""

from __future__ import annotations

import random
import tkinter as tk
from pathlib import Path
from typing import Any

from PIL import Image, ImageTk


AVATAR_ROOT = (
    Path(__file__).resolve().parents[2]
    / "chappie"
    / "assets"
    / "avatar"
    / "states"
)

IDLE_ROOT = AVATAR_ROOT / "idle"


class ChappieAvatar:
    """Manage Chappie's visual state and lightweight idle animation."""

    def __init__(
        self,
        scheduler: Any,
        *,
        display_width: int = 260,
    ) -> None:
        self.scheduler = scheduler
        self.display_width = display_width

        self._images = self._load_idle_images()
        self._current_image = self._images["neutral"]

        self._label: Any | None = None

        # Runtime state.
        self._active = False
        self._generation = 0
        self._motion: str | None = None

    @property
    def image(self) -> ImageTk.PhotoImage:
        """Return the image used when constructing the avatar label."""
        return self._current_image

    def attach(self, label: Any) -> None:
        """Attach the rendered Bootstack label to the animator."""
        self._label = label

    def start_idle(self) -> None:
        """Enter ambient idle animation if it is not already running."""

        # render() may publish IDLE/SLEEPING repeatedly. Do not create
        # another pair of timer chains every time that happens.
        if self._active:
            return

        self._generation += 1
        generation = self._generation

        self._active = True
        self._motion = None
        self._show("neutral")

        self._schedule_blink(generation)
        self._schedule_glance(generation)

    def stop(self) -> None:
        """Stop idle animation and return to the neutral frame."""

        if not self._active:
            self._show("neutral")
            return

        # Existing callbacks may still fire, but their generation token
        # becomes stale and they immediately return.
        self._generation += 1
        self._active = False
        self._motion = None
        self._show("neutral")

    def _load_idle_images(self) -> dict[str, ImageTk.PhotoImage]:
        paths = {
            "neutral": IDLE_ROOT / "idle_neutral.png",
            "look_left": IDLE_ROOT / "idle_look_left.png",
            "look_right": IDLE_ROOT / "idle_look_right.png",
            "blink_half": IDLE_ROOT / "idle_blink_half.png",
            "blink_closed": IDLE_ROOT / "idle_blink_closed.png",
        }

        images: dict[str, ImageTk.PhotoImage] = {}

        for name, path in paths.items():
            if not path.is_file():
                raise FileNotFoundError(
                    f"Chappie avatar frame not found: {path}"
                )

            with Image.open(path) as source:
                source = source.convert("RGBA")

                ratio = self.display_width / source.width
                display_height = max(
                    1,
                    round(source.height * ratio),
                )

                rendered = source.resize(
                    (self.display_width, display_height),
                    Image.Resampling.LANCZOS,
                )

                images[name] = ImageTk.PhotoImage(rendered)

        return images

    def _show(self, frame: str) -> None:
        image = self._images[frame]
        self._current_image = image

        if self._label is not None:
            # Keep an explicit reference because Tk images disappear if
            # Python garbage-collects the backing PhotoImage object.
            self._label.image = image

    # ------------------------------------------------------------------
    # Blink behavior
    # ------------------------------------------------------------------

    def _schedule_blink(self, generation: int) -> None:
        delay_ms = random.randint(2_800, 7_500)

        self.scheduler.after(
            delay_ms,
            lambda: self._begin_blink(generation),
        )

    def _begin_blink(self, generation: int) -> None:
        if not self._is_current(generation):
            return

        if self._motion is not None:
            self._retry_blink(generation)
            return

        self._motion = "blink"
        self._show("blink_half")

        self.scheduler.after(
            random.randint(45, 70),
            lambda: self._blink_closed(generation),
        )

    def _blink_closed(self, generation: int) -> None:
        if not self._is_motion_current(generation, "blink"):
            return

        self._show("blink_closed")

        self.scheduler.after(
            random.randint(70, 115),
            lambda: self._blink_opening(generation),
        )

    def _blink_opening(self, generation: int) -> None:
        if not self._is_motion_current(generation, "blink"):
            return

        self._show("blink_half")

        self.scheduler.after(
            random.randint(45, 70),
            lambda: self._finish_blink(generation),
        )

    def _finish_blink(self, generation: int) -> None:
        if not self._is_motion_current(generation, "blink"):
            return

        self._show("neutral")

        # A small percentage of natural blinks occur as a quick pair.
        if random.random() < 0.14:
            self.scheduler.after(
                random.randint(110, 220),
                lambda: self._begin_second_blink(generation),
            )
            return

        self._motion = None
        self._schedule_blink(generation)

    def _begin_second_blink(self, generation: int) -> None:
        if not self._is_motion_current(generation, "blink"):
            return

        self._show("blink_half")

        self.scheduler.after(
            random.randint(45, 65),
            lambda: self._second_blink_closed(generation),
        )

    def _second_blink_closed(self, generation: int) -> None:
        if not self._is_motion_current(generation, "blink"):
            return

        self._show("blink_closed")

        self.scheduler.after(
            random.randint(65, 100),
            lambda: self._second_blink_opening(generation),
        )

    def _second_blink_opening(self, generation: int) -> None:
        if not self._is_motion_current(generation, "blink"):
            return

        self._show("blink_half")

        self.scheduler.after(
            random.randint(45, 65),
            lambda: self._finish_second_blink(generation),
        )

    def _finish_second_blink(self, generation: int) -> None:
        if not self._is_motion_current(generation, "blink"):
            return

        self._show("neutral")
        self._motion = None
        self._schedule_blink(generation)

    def _retry_blink(self, generation: int) -> None:
        if not self._is_current(generation):
            return

        self.scheduler.after(
            random.randint(350, 900),
            lambda: self._begin_blink(generation),
        )

    # ------------------------------------------------------------------
    # Glance behavior
    # ------------------------------------------------------------------

    def _schedule_glance(self, generation: int) -> None:
        delay_ms = random.randint(5_500, 14_000)

        self.scheduler.after(
            delay_ms,
            lambda: self._begin_glance(generation),
        )

    def _begin_glance(self, generation: int) -> None:
        if not self._is_current(generation):
            return

        if self._motion is not None:
            self._retry_glance(generation)
            return

        self._motion = "glance"

        frame = random.choice(
            ("look_left", "look_right")
        )
        self._show(frame)

        self.scheduler.after(
            random.randint(400, 1_050),
            lambda: self._finish_glance(generation),
        )

    def _finish_glance(self, generation: int) -> None:
        if not self._is_motion_current(generation, "glance"):
            return

        self._show("neutral")
        self._motion = None
        self._schedule_glance(generation)

    def _retry_glance(self, generation: int) -> None:
        if not self._is_current(generation):
            return

        self.scheduler.after(
            random.randint(500, 1_200),
            lambda: self._begin_glance(generation),
        )

    # ------------------------------------------------------------------
    # State guards
    # ------------------------------------------------------------------

    def _is_current(self, generation: int) -> bool:
        return (
            self._active
            and generation == self._generation
        )

    def _is_motion_current(
        self,
        generation: int,
        motion: str,
    ) -> bool:
        return (
            self._is_current(generation)
            and self._motion == motion
        )
