import platform
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

from services.models import (
    CpuStatus,
    DiskStatus,
    MemoryStatus,
    SystemStatus,
)


class SystemService:
    """Collect safe, read-only health information about the local machine."""

    def __init__(self, disk_path: Path | str = "/") -> None:
        self.disk_path = Path(disk_path)

    def get_status(self) -> SystemStatus:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(str(self.disk_path))

        return SystemStatus(
            hostname=socket.gethostname(),
            platform=platform.platform(),
            uptime_seconds=max(0, int(time.time() - psutil.boot_time())),
            cpu=CpuStatus(
                usage_percent=psutil.cpu_percent(interval=0.2),
                temperature_celsius=self._read_cpu_temperature(),
            ),
            memory=MemoryStatus(
                total_bytes=memory.total,
                available_bytes=memory.available,
                usage_percent=memory.percent,
            ),
            disk=DiskStatus(
                total_bytes=disk.total,
                free_bytes=disk.free,
                usage_percent=disk.percent,
            ),
            collected_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _read_cpu_temperature() -> float | None:
        """Return the Raspberry Pi CPU temperature when available."""

        thermal_file = Path("/sys/class/thermal/thermal_zone0/temp")

        try:
            raw_value = thermal_file.read_text(encoding="utf-8").strip()
            return round(int(raw_value) / 1000, 1)
        except (FileNotFoundError, PermissionError, ValueError, OSError):
            return None
