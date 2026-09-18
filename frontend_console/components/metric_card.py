"""Reusable metric card for the Psydekik console."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import bootstack as bs


@dataclass(slots=True)
class MetricCard:
    """A compact dashboard metric with optional percentage bar."""

    value_label: Any
    detail_label: Any
    progress_bar: Any | None = None

    @classmethod
    def build(
        cls,
        title: str,
        *,
        icon: str,
        accent: str = "primary",
        show_progress: bool = False,
    ) -> "MetricCard":
        """Render a metric card in the current Bootstack container."""

        with bs.Card(
            padding=18,
            gap=8,
            grow_items=True,
            horizontal_items="stretch",
        ):
            bs.Label(
                title.upper(),
                icon=icon,
                accent="muted",
            )
            value_label = bs.Label(
                "--",
                font="heading-lg",
                accent=accent,
            )
            detail_label = bs.Label(
                "Waiting for live data",
                accent="muted",
            )
            progress_bar = None

            if show_progress:
                progress_bar = bs.ProgressBar(
                    value=0,
                    max_value=100,
                    accent=accent,
                    variant="thin",
                )

        return cls(
            value_label=value_label,
            detail_label=detail_label,
            progress_bar=progress_bar,
        )

    def update(
        self,
        value: str,
        detail: str,
        *,
        progress: float | None = None,
    ) -> None:
        """Update the card using Bootstack's public widget properties."""

        self.value_label.text = value
        self.detail_label.text = detail

        if self.progress_bar is not None and progress is not None:
            self.progress_bar.value = progress
