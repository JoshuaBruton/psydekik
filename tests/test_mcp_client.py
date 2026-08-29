import pytest

from chappie.mcp_client import ChappieMCPClient


@pytest.mark.anyio
async def test_chappie_can_call_system_status() -> None:
    async with ChappieMCPClient() as client:
        tool_names = await client.list_tool_names()
        status = await client.get_system_status()

    assert "get_system_status" in tool_names
    assert status["hostname"]
    assert status["uptime_seconds"] >= 0
    assert 0 <= status["cpu"]["usage_percent"] <= 100
    assert 0 <= status["memory"]["usage_percent"] <= 100
    assert 0 <= status["disk"]["usage_percent"] <= 100
