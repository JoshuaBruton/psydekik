
"""Psydekik's native Bootstack console."""

from __future__ import annotations

import bootstack as bs


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
                        bs.Label(
                            "Online",
                            font="heading-lg",
                            accent="success",
                        )
                        bs.Label(
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
                        bs.Label("CPU: --")
                        bs.Label("Temperature: --")
                        bs.Label("Memory: --")
                        bs.Label("Disk: --")
                        bs.Label("Uptime: --")

                    bs.ProgressBar(
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

    return shell


def main() -> None:
    """Start the Psydekik desktop console."""

    app = build_app()
    app.run()


if __name__ == "__main__":
    main()
