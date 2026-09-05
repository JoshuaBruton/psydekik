"""Process-wide shutdown state for Chappie's voice runtime."""

from __future__ import annotations

import signal
from threading import Event


class ShutdownController:
    """Coordinate graceful shutdown across blocking voice loops."""

    def __init__(self) -> None:
        self._event = Event()

    @property
    def requested(self) -> bool:
        return self._event.is_set()

    def request(self) -> None:
        self._event.set()

    def install_signal_handlers(self) -> None:
        signal.signal(
            signal.SIGINT,
            self._handle_sigint,
        )
        signal.signal(
            signal.SIGTERM,
            self._handle_sigterm,
        )

    def _handle_sigint(
        self,
        signum,
        frame,
    ) -> None:
        del signum, frame

        if not self._event.is_set():
            print()
            print("Shutdown requested...")
            self._event.set()

    def _handle_sigterm(
        self,
        signum,
        frame,
    ) -> None:
        del signum, frame
        self._event.set()


shutdown = ShutdownController()
