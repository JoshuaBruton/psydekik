"""Nonblocking system-status polling for the console."""

from __future__ import annotations

from collections.abc import Callable
from queue import Empty, Queue
from threading import Thread
from typing import TypeAlias

from frontend_console.api.client import (
    PsydekikApiClient,
    PsydekikApiError,
)
from frontend_console.api.models import SystemStatus


PollResult: TypeAlias = SystemStatus | Exception
StatusHandler: TypeAlias = Callable[[SystemStatus], None]
ErrorHandler: TypeAlias = Callable[[Exception], None]


class SystemStatusPoller:
    """Fetch system status without blocking Tk's event loop."""

    def __init__(
        self,
        scheduler,
        on_status: StatusHandler,
        on_error: ErrorHandler,
        *,
        client: PsydekikApiClient | None = None,
        interval_ms: int = 5_000,
    ) -> None:
        self.scheduler = scheduler
        self.on_status = on_status
        self.on_error = on_error
        self.client = client or PsydekikApiClient()
        self.interval_ms = interval_ms

        self._results: Queue[PollResult] = Queue()
        self._running = False
        self._request_active = False
        self._after_id: str | None = None

    def start(self) -> None:
        """Start polling immediately."""

        if self._running:
            return

        self._running = True
        self._poll()
        self._drain_results()

    def stop(self) -> None:
        """Stop scheduling new requests."""

        self._running = False

        if self._after_id is not None:
            try:
                self.scheduler.after_cancel(
                    self._after_id
                )
            except Exception:
                pass

            self._after_id = None

    def _poll(self) -> None:
        """Start one daemon worker when no request is active."""

        if not self._running or self._request_active:
            return

        self._request_active = True

        worker = Thread(
            target=self._fetch,
            name="psydekik-system-poller",
            daemon=True,
        )
        worker.start()

    def _fetch(self) -> None:
        """Fetch one result inside the worker thread."""

        try:
            result: PollResult = (
                self.client.get_system_status()
            )
        except (
            PsydekikApiError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            result = exc
        except Exception as exc:
            result = exc

        self._results.put(result)

    def _drain_results(self) -> None:
        """Deliver worker results on Tk's main thread."""

        if not self._running:
            return

        try:
            result = self._results.get_nowait()
        except Empty:
            self._after_id = self.scheduler.after(
                100,
                self._drain_results,
            )
            return

        self._request_active = False

        if isinstance(result, SystemStatus):
            self.on_status(result)
        else:
            self.on_error(result)

        self._after_id = self.scheduler.after(
            self.interval_ms,
            self._next_cycle,
        )

    def _next_cycle(self) -> None:
        """Begin the next scheduled poll."""

        if not self._running:
            return

        self._poll()
        self._drain_results()
