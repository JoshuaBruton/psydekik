from contextlib import AsyncExitStack
from typing import Any, Self

from mcp import Client

from mcp_server.server import mcp


class ChappieMCPClient:
    """Manage Chappie's connection to the Psydekik MCP server."""

    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None
        self._client: Client | None = None

    async def __aenter__(self) -> Self:
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        self._client = await self._stack.enter_async_context(
            Client(mcp, raise_exceptions=True)
        )

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        if self._stack is not None:
            await self._stack.__aexit__(
                exc_type,
                exc_value,
                traceback,
            )

        self._client = None
        self._stack = None

    @property
    def client(self) -> Client:
        """Return the connected MCP client."""

        if self._client is None:
            raise RuntimeError(
                "ChappieMCPClient is not connected. "
                "Use it inside 'async with'."
            )

        return self._client

    async def list_tool_names(self) -> list[str]:
        """Return the names of all available Psydekik tools."""

        result = await self.client.list_tools()
        return [tool.name for tool in result.tools]

    async def get_system_status(self) -> dict[str, Any]:
        """Request the Raspberry Pi's system status through MCP."""

        result = await self.client.call_tool(
            "get_system_status",
            {},
        )

        if result.is_error:
            raise RuntimeError(
                f"get_system_status failed: {result.content}"
            )

        if result.structured_content is None:
            raise RuntimeError(
                "get_system_status returned no structured content."
            )

        return result.structured_content
