"""Continuous background worker for Psydekik's file organizer."""

from __future__ import annotations

import logging
import signal
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Lock
from typing import Final

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from services.file_organizer_service import FileOrganizerService


LOGGER = logging.getLogger("psydekik.file_organizer")

STABILITY_INTERVAL: Final[float] = 0.5
STABILITY_CHECKS_REQUIRED: Final[int] = 3
STABILITY_TIMEOUT: Final[float] = 30.0


class OrganizerEventHandler(FileSystemEventHandler):
    """Translate filesystem events into safe worker-queue entries."""

    def __init__(self, worker: FileOrganizerWorker) -> None:
        super().__init__()
        self.worker = worker

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self.worker.enqueue(Path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            destination = getattr(event, "dest_path", None)

            if destination:
                self.worker.enqueue(Path(destination))


class FileOrganizerWorker:
    """Watch the organizer inbox and process stable files sequentially."""

    def __init__(
        self,
        service: FileOrganizerService | None = None,
    ) -> None:
        self.service = service or FileOrganizerService()
        self.queue: Queue[Path] = Queue()
        self.stop_event = Event()

        self._queued_paths: set[Path] = set()
        self._queue_lock = Lock()

        self.observer = Observer()
        self.handler = OrganizerEventHandler(self)

    def enqueue(self, file_path: Path) -> None:
        path = file_path.expanduser().resolve()

        if path.parent != self.service.inbox:
            LOGGER.warning("Ignoring path outside inbox: %s", path)
            return

        if self.service.is_ignored(path):
            LOGGER.debug("Ignoring temporary or hidden file: %s", path)
            return

        with self._queue_lock:
            if path in self._queued_paths:
                return

            self._queued_paths.add(path)

        self.queue.put(path)
        LOGGER.info("Queued file: %s", path.name)

    def _remove_from_pending_set(self, path: Path) -> None:
        with self._queue_lock:
            self._queued_paths.discard(path)

    def enqueue_existing_files(self) -> None:
        pending = self.service.pending_files()

        if pending:
            LOGGER.info(
                "Found %d file(s) waiting at startup.",
                len(pending),
            )

        for path in pending:
            self.enqueue(path)

    def wait_until_stable(self, path: Path) -> bool:
        """Wait until a file's size remains unchanged across several checks."""

        deadline = time.monotonic() + STABILITY_TIMEOUT
        previous_size: int | None = None
        stable_checks = 0

        while (
            not self.stop_event.is_set()
            and time.monotonic() < deadline
        ):
            if not path.exists():
                LOGGER.info(
                    "File disappeared before processing: %s",
                    path.name,
                )
                return False

            if not path.is_file():
                return False

            try:
                current_size = path.stat().st_size
            except OSError:
                stable_checks = 0
                time.sleep(STABILITY_INTERVAL)
                continue

            if current_size == previous_size:
                stable_checks += 1
            else:
                previous_size = current_size
                stable_checks = 0

            if stable_checks >= STABILITY_CHECKS_REQUIRED:
                return True

            time.sleep(STABILITY_INTERVAL)

        if not self.stop_event.is_set():
            LOGGER.error(
                "Timed out waiting for file to stabilize: %s",
                path.name,
            )

        return False

    def process_path(self, path: Path) -> None:
        try:
            if not self.wait_until_stable(path):
                return

            result = self.service.organize(path)

            if result.status == "organized":
                LOGGER.info(
                    "Organized %s -> %s",
                    Path(result.source).name,
                    result.destination,
                )
            else:
                LOGGER.warning(
                    "%s: %s",
                    result.status,
                    result.message,
                )

        except Exception:
            LOGGER.exception(
                "Failed to organize file: %s",
                path,
            )

        finally:
            self._remove_from_pending_set(path)

    def run(self) -> None:
        LOGGER.info(
            "Starting Psydekik file organizer. Watching: %s",
            self.service.inbox,
        )

        self.observer.schedule(
            self.handler,
            str(self.service.inbox),
            recursive=False,
        )
        self.observer.start()
        self.enqueue_existing_files()

        try:
            while not self.stop_event.is_set():
                try:
                    path = self.queue.get(timeout=0.5)
                except Empty:
                    continue

                try:
                    self.process_path(path)
                finally:
                    self.queue.task_done()

        finally:
            LOGGER.info("Stopping filesystem observer.")
            self.observer.stop()
            self.observer.join(timeout=5)
            LOGGER.info("Psydekik file organizer stopped.")

    def stop(self) -> None:
        self.stop_event.set()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )


def main() -> None:
    configure_logging()
    worker = FileOrganizerWorker()

    def request_shutdown(
        signum: int,
        _frame: object,
    ) -> None:
        LOGGER.info("Received signal %s; requesting shutdown.", signum)
        worker.stop()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    worker.run()


if __name__ == "__main__":
    main()
