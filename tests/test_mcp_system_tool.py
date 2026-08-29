from mcp_server.tools.system import get_system_status


def test_get_system_status_tool() -> None:
    result = get_system_status()

    assert result["hostname"]
    assert result["uptime_seconds"] >= 0

    assert 0 <= result["cpu"]["usage_percent"] <= 100
    assert 0 <= result["memory"]["usage_percent"] <= 100
    assert 0 <= result["disk"]["usage_percent"] <= 100

    assert "collected_at" in result
