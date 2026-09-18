"""Home dashboard for Psydekik's native console."""

from __future__ import annotations

from typing import Any

import bootstack as bs

from frontend_console.api.models import (
    SystemStatus,
    format_bytes,
    format_uptime,
)
from frontend_console.components.metric_card import MetricCard


class HomePage:
    """Build and update the live bento-style home dashboard."""

    def __init__(self) -> None:
        self.connection_label: Any
        self.last_updated_label: Any
        self.uptime_label: Any
        self.platform_label: Any

        with bs.Column(
            padding=24,
            gap=18,
            horizontal_items="stretch",
        ):
            bs.Label(
                "Psydekik",
                font="heading-xl",
            )
            bs.Label(
                "Chappie's family command center",
                accent="muted",
            )

            with bs.Row(
                gap=16,
                grow_items=True,
                weights=[2, 1],
                vertical_items="stretch",
            ):
                self._build_chappie_card()

                with bs.Column(
                    gap=16,
                    grow_items=True,
                    horizontal_items="stretch",
                ):
                    self._build_system_card()
                    self._build_family_card()

            with bs.Row(
                gap=16,
                grow_items=True,
                vertical_items="stretch",
            ):
                self.cpu_card = MetricCard.build(
                    "CPU",
                    icon="cpu-fill",
                    accent="info",
                    show_progress=True,
                )
                self.temperature_card = MetricCard.build(
                    "Temperature",
                    icon="thermometer-half",
                    accent="warning",
                    show_progress=True,
                )
                self.memory_card = MetricCard.build(
                    "Memory",
                    icon="memory",
                    accent="primary",
                    show_progress=True,
                )
                self.disk_card = MetricCard.build(
                    "Storage",
                    icon="device-hdd-fill",
                    accent="success",
                    show_progress=True,
                )

            with bs.Card(
                padding=18,
                gap=8,
                horizontal_items="stretch",
            ):
                bs.Label(
                    "RASPBERRY PI",
                    icon="motherboard-fill",
                    accent="muted",
                )
                self.uptime_label = bs.Label(
                    "Uptime --",
                    font="heading-md",
                )
                self.platform_label = bs.Label(
                    "Waiting for host details",
                    accent="muted",
                    wrap_width=760,
                )

    def _build_chappie_card(self) -> None:
        with bs.Card(
            padding=22,
            gap=12,
            grow_items=True,
            horizontal_items="stretch",
            accent="primary",
        ):
            bs.Label(
                "CHAPPIE",
                icon="stars",
                accent="muted",
            )
            bs.Label(
                "Ready when you are, sir.",
                font="heading-lg",
                accent="primary",
            )
            bs.Label(
                "Idle · Voice online",
                accent="success",
            )
            bs.Label(
                "Conversation, reminders, family coordination, and "
                "home intelligence will gather here.",
                accent="muted",
                wrap_width=560,
            )

    def _build_system_card(self) -> None:
        with bs.Card(
            padding=18,
            gap=8,
            grow_items=True,
            horizontal_items="stretch",
        ):
            bs.Label(
                "SYSTEM",
                icon="activity",
                accent="muted",
            )
            self.connection_label = bs.Label(
                "Connecting...",
                font="heading-md",
                accent="warning",
            )
            self.last_updated_label = bs.Label(
                "Waiting for live API data",
                accent="muted",
            )

    @staticmethod
    def _build_family_card() -> None:
        with bs.Card(
            padding=18,
            gap=8,
            grow_items=True,
            horizontal_items="stretch",
        ):
            bs.Label(
                "FAMILY",
                icon="people-fill",
                accent="muted",
            )
            bs.Label(
                "Connected",
                font="heading-md",
            )
            bs.Label(
                "Shared services are next",
                accent="muted",
            )

    def show_status(self, status: SystemStatus) -> None:
        """Apply a fresh API status snapshot to the dashboard."""

        self.connection_label.text = f"{status.hostname} online"
        self.last_updated_label.text = (
            "Updated "
            f"{status.collected_at.astimezone():%I:%M:%S %p}"
        )
        self.cpu_card.update(
            f"{status.cpu.usage_percent:.1f}%",
            "Current processor load",
            progress=status.cpu.usage_percent,
        )
        self.temperature_card.update(
            f"{status.cpu.temperature_celsius:.1f}°C",
            "CPU temperature",
            progress=status.cpu.temperature_celsius,
        )
        self.memory_card.update(
            f"{status.memory.usage_percent:.1f}%",
            f"{format_bytes(status.memory.available_bytes)} available",
            progress=status.memory.usage_percent,
        )
        self.disk_card.update(
            f"{status.disk.usage_percent:.1f}%",
            f"{format_bytes(status.disk.free_bytes)} free",
            progress=status.disk.usage_percent,
        )
        self.uptime_label.text = (
            f"Uptime {format_uptime(status.uptime_seconds)}"
        )
        self.platform_label.text = (
            f"{status.hostname} · {status.platform}"
        )

    def show_error(self, error: Exception) -> None:
        """Show a friendly disconnected state while retaining stale data."""

        self.connection_label.text = "API offline"
        self.last_updated_label.text = str(error)
