from services.models import SystemStatus
from services.system_service import SystemService


def test_get_status_returns_valid_model() -> None:
    status = SystemService().get_status()

    assert isinstance(status, SystemStatus)
    assert status.hostname
    assert status.uptime_seconds >= 0

    assert 0 <= status.cpu.usage_percent <= 100
    assert 0 <= status.memory.usage_percent <= 100
    assert 0 <= status.disk.usage_percent <= 100

    assert status.memory.total_bytes > 0
    assert status.disk.total_bytes > 0


def test_status_serializes_to_json() -> None:
    status = SystemService().get_status()
    serialized = status.model_dump()

    assert serialized["hostname"] == status.hostname
    assert "cpu" in serialized
    assert "memory" in serialized
    assert "disk" in serialized
    assert "collected_at" in serialized
