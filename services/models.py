from datetime import datetime

from pydantic import BaseModel, Field


class CpuStatus(BaseModel):
    usage_percent: float = Field(ge=0, le=100)
    temperature_celsius: float | None = None


class MemoryStatus(BaseModel):
    total_bytes: int = Field(ge=0)
    available_bytes: int = Field(ge=0)
    usage_percent: float = Field(ge=0, le=100)


class DiskStatus(BaseModel):
    total_bytes: int = Field(ge=0)
    free_bytes: int = Field(ge=0)
    usage_percent: float = Field(ge=0, le=100)


class SystemStatus(BaseModel):
    hostname: str
    platform: str
    uptime_seconds: int = Field(ge=0)
    cpu: CpuStatus
    memory: MemoryStatus
    disk: DiskStatus
    collected_at: datetime
