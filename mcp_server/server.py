from mcp.server import MCPServer

from mcp_server.tools.system import register_system_tools


mcp = MCPServer("psydekik")

register_system_tools(mcp)


def main() -> None:
    """Start the Psydekik MCP server over standard input/output."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
