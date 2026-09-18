
"""Psydekik's native Bootstack console."""

from __future__ import annotations

from typing import Any

import bootstack as bs

from frontend_console.api.models import (
    SystemStatus,
    format_bytes,
    format_uptime,
)
from frontend_console.state.system_state import SystemStatusPoller


APP_TITLE = "Psydekik: Chappie"
APP_THEME = "nord-dark"
APP_SIZE = (1200, 760)


def build_app() -> bs.AppShell:
    """Build and return the Psydekik desktop console."""

    shell = bs.AppShell(
        title=APP_TITLE,
        size=APP_SIZE,
        min_size=(900, 600),
        theme=APP_THEME,
        sidebar_mode="expanded",
        sidebar_width=220,
        collapsible=True,
        nav_accent="primary",
        show_statusbar=True,
        remember_window_state=True,
    )

    widgets: dict[str, Any] = {}

    with shell.page_nav() as nav:
        with nav.add_page(
            "home",
            text="Home",
            icon="house-fill",
        ):
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
                    vertical_items="stretch",
                ):
                    with bs.Card(
                        padding=18,
                        gap=8,
                        grow_items=True,
                    ):
                        bs.Label(
                            "SYSTEM",
                            accent="muted",
                        )
                        widgets["connection"] = bs.Label(
                            "Connecting...",
                            font="heading-lg",
                            accent="warning",
                        )
                        widgets["last_updated"] = bs.Label(
                            "Waiting for live API data",
                            accent="muted",
                        )

                    with bs.Card(
                        padding=18,
                        gap=8,
                        grow_items=True,
                    ):
                        bs.Label(
                            "CHAPPIE",
                            accent="muted",
                        )
                        bs.Label(
                            "Idle",
                            font="heading-lg",
                            accent="primary",
                        )
                        bs.Label(
                            "Ready when you are, sir.",
                            accent="muted",
                        )

                    with bs.Card(
                        padding=18,
                        gap=8,
                        grow_items=True,
                    ):
                        bs.Label(
                            "FAMILY",
                            accent="muted",
                        )
                        bs.Label(
                            "Connected",
                            font="heading-lg",
                        )
                        bs.Label(
                            "Family services coming next",
                            accent="muted",
                        )

                with bs.Card(
                    padding=20,
                    gap=12,
                    horizontal_items="stretch",
                ):
                    bs.Label(
                        "System overview",
                        font="heading-md",
                    )

                    with bs.Row(
                        gap=16,
                        grow_items=True,
                    ):
                        widgets["cpu"] = bs.Label(
                            "CPU: --",
                            font="heading-sm",
                        )
                        widgets["temperature"] = bs.Label(
                            "Temperature: --",
                            font="heading-sm",
                        )
                        widgets["memory"] = bs.Label(
                            "Memory: --",
                            font="heading-sm",
                        )
                        widgets["disk"] = bs.Label(
                            "Disk: --",
                            font="heading-sm",
                        )
                        widgets["uptime"] = bs.Label(
                            "Uptime: --",
                            font="heading-sm",
                        )

                    widgets["memory_bar"] = bs.ProgressBar(
                        value=0,
                        max_value=100,
                        accent="primary",
                    )

        with nav.add_page(
            "chappie",
            text="Chappie",
            icon="chat-dots-fill",
        ):
            with bs.Column(
                padding=24,
                gap=16,
                horizontal_items="stretch",
            ):
                bs.Label(
                    "Chappie",
                    font="heading-xl",
                )
                bs.Label(
                    "Conversation and voice activity",
                    accent="muted",
                )

                with bs.Card(
                    padding=20,
                    gap=12,
                    grow_items=True,
                ):
                    bs.Label(
                        "Chappie is idle.",
                        font="heading-md",
                        accent="primary",
                    )
                    bs.Label(
                        "Listening, transcription, thinking, "
                        "and speaking states will appear here.",
                        wrap_width=700,
                    )

        with nav.add_page(
            "system",
            text="System",
            icon="cpu-fill",
        ):
            with bs.Column(
                padding=24,
                gap=16,
                horizontal_items="stretch",
            ):
                bs.Label(
                    "System",
                    font="heading-xl",
                )
                bs.Label(
                    "Raspberry Pi health and services",
                    accent="muted",
                )

                with bs.Card(
                    padding=20,
                    gap=12,
                ):
                    bs.Label(
                        "bru-raspi",
                        font="heading-md",
                    )
                    bs.Badge(
                        "API status pending",
                        accent="warning",
                        variant="pill",
                    )

        with nav.add_page(
            "settings",
            text="Settings",
            icon="gear-fill",
        ):
            with bs.Column(
                padding=24,
                gap=16,
                horizontal_items="stretch",
            ):
                bs.Label(
                    "Settings",
                    font="heading-xl",
                )
                bs.Label(
                    "Console, voice, theme, and connection settings",
                    accent="muted",
                )

                with bs.Card(
                    padding=20,
                    gap=12,
                ):
                    bs.Label(
                        "Appearance",
                        font="heading-md",
                    )
                    bs.Label("Current theme: Nord Dark")
                    bs.ThemeToggle()

    def show_status(status: SystemStatus) -> None:
        """Apply fresh API data to the dashboard."""

        widgets["connection"].configure(
            text=f"{status.hostname} online"
        )
        widgets["last_updated"].configure(
            text=(
                "Updated "
                f"{status.collected_at.astimezone():%I:%M:%S %p}"
            )
        )
        widgets["cpu"].configure(
            text=f"CPU: {status.cpu.usage_percent:.1f}%"
        )
        widgets["temperature"].configure(
            text=(
                "Temperature: "
                f"{status.cpu.temperature_celsius:.1f}°C"
            )
        )
        widgets["memory"].configure(
            text=(
                f"Memory: {status.memory.usage_percent:.1f}%"
                " · "
                f"{format_bytes(status.memory.available_bytes)} free"
            )
        )
        widgets["disk"].configure(
            text=(
                f"Disk: {status.disk.usage_percent:.1f}%"
                " · "
                f"{format_bytes(status.disk.free_bytes)} free"
            )
        )
        widgets["uptime"].configure(
            text=(
                "Uptime: "
                f"{format_uptime(status.uptime_seconds)}"
            )
        )
        widgets["memory_bar"].configure(
            value=status.memory.usage_percent
        )

    def show_error(error: Exception) -> None:
        """Show a friendly disconnected state."""

        widgets["connection"].configure(
            text="API offline"
        )
        widgets["last_updated"].configure(
            text=str(error)
        )

    poller = SystemStatusPoller(
        shell._internal,
        show_status,
        show_error,
        interval_ms=5_000,
    )

    shell._internal.after(250, poller.start)

    return shell


def main() -> None:
    """Start the Psydekik desktop console."""

    app = build_app()
    app.run()


if __name__ == "__main__":
    main()
