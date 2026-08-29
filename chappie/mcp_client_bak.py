import asyncio
import json

from mcp import Client

from mcp_server.server import mcp


async def main() -> None:
    """Test the Psydekik MCP server using an in-process connection."""

    async with Client(mcp, raise_exceptions=True) as client:
        print("Connected to:", client.server_info)
        print("Protocol:", client.protocol_version)

        tools_result = await client.list_tools()
        tool_names = [tool.name for tool in tools_result.tools]

        print("Available tools:", tool_names)

        result = await client.call_tool(
            "get_system_status",
            {},
        )

        if result.is_error:
            raise RuntimeError(
                f"get_system_status failed: {result.content}"
            )

        print("\nSystem status returned through MCP:")
        print(
            json.dumps(
                result.structured_content,
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
