"""Psydekik's native Bootstack console."""

from __future__ import annotations

import bootstack as bs

from frontend_console.pages.home import HomePage
from frontend_console.state.chappie_state import (
    ChappieVoiceController,
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

    with shell.page_nav() as nav:
        with nav.add_page(
            "home",
            text="Home",
            icon="house-fill",
        ):
            home_page = HomePage()

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

    poller = SystemStatusPoller(
        shell._internal,
        home_page.show_status,
        home_page.show_error,
        interval_ms=5_000,
    )

    voice_controller = ChappieVoiceController(
        shell._internal,
        home_page.show_chappie_state,
    )
    home_page.bind_talk(voice_controller.request_turn)

    shell._internal.after(250, poller.start)
    shell._internal.after(500, voice_controller.start)

    return shell


def main() -> None:
    """Start the Psydekik desktop console."""

    app = build_app()
    app.run()


if __name__ == "__main__":
    main()
