from typing import Any

from mcp.server import MCPServer

from services.system_service import SystemService


system_service = SystemService()


def get_system_status() -> dict[str, Any]:
    """Return current CPU, memory, disk, temperature, and uptime data."""

    status = system_service.get_status()
    return status.model_dump(mode="json")


def register_system_tools(server: MCPServer) -> None:
    """Register Psydekik system tools with the MCP server."""

    server.tool()(get_system_status)
