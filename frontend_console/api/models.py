"""Typed models for the Psydekik Console."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class CpuStatus:
    usage_percent: float
    temperature_celsius: float


@dataclass(frozen=True, slots=True)
class MemoryStatus:
    total_bytes: int
    available_bytes: int
    usage_percent: float


@dataclass(frozen=True, slots=True)
class DiskStatus:
    total_bytes: int
    free_bytes: int
    usage_percent: float


@dataclass(frozen=True, slots=True)
class SystemStatus:
    hostname: str
    platform: str
    uptime_seconds: int
    cpu: CpuStatus
    memory: MemoryStatus
    disk: DiskStatus
    collected_at: datetime

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SystemStatus:
        cpu = data["cpu"]
        memory = data["memory"]
        disk = data["disk"]
        timestamp = str(data["collected_at"]).replace(
            "Z",
            "+00:00",
        )

        return cls(
            hostname=str(data["hostname"]),
            platform=str(data["platform"]),
            uptime_seconds=int(data["uptime_seconds"]),
            cpu=CpuStatus(
                usage_percent=float(cpu["usage_percent"]),
                temperature_celsius=float(
                    cpu["temperature_celsius"]
                ),
            ),
            memory=MemoryStatus(
                total_bytes=int(memory["total_bytes"]),
                available_bytes=int(
                    memory["available_bytes"]
                ),
                usage_percent=float(
                    memory["usage_percent"]
                ),
            ),
            disk=DiskStatus(
                total_bytes=int(disk["total_bytes"]),
                free_bytes=int(disk["free_bytes"]),
                usage_percent=float(
                    disk["usage_percent"]
                ),
            ),
            collected_at=datetime.fromisoformat(timestamp),
        )


def format_bytes(byte_count: int) -> str:
    value = float(byte_count)

    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            precision = 1 if unit in {"GiB", "TiB"} else 0
            return f"{value:.{precision}f} {unit}"

        value /= 1024

    return f"{value:.1f} TiB"


def format_uptime(total_seconds: int) -> str:
    days, remainder = divmod(total_seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, _ = divmod(remainder, 60)

    if days:
        return f"{days}d {hours}h {minutes}m"

    if hours:
        return f"{hours}h {minutes}m"

    return f"{minutes}m"

