import asyncio
from typing import Any, Protocol

from chappie.mcp_client import ChappieMCPClient


class MCPClientProtocol(Protocol):
    """Describe the MCP functionality required by the orchestrator."""

    async def get_system_status(self) -> dict[str, Any]:
        """Return current Raspberry Pi system information."""


class ChappieOrchestrator:
    """Interpret user requests and coordinate Psydekik tools."""

    SYSTEM_STATUS_PHRASES = (
        "system status",
        "pi status",
        "raspberry pi",
        "cpu",
        "memory",
        "temperature",
        "disk space",
        "uptime",
        "how is the pi",
        "how's the pi",
        "how is psydekik",
        "how's psydekik",
    )

    def __init__(self, mcp_client: MCPClientProtocol) -> None:
        self.mcp_client = mcp_client

    async def handle_message(self, message: str) -> str:
        """Route a user message and return Chappie's response."""

        normalized_message = message.casefold().strip()

        if not normalized_message:
            return "I didn't hear a request. Try asking how the Pi is doing."

        if self._requests_system_status(normalized_message):
            status = await self.mcp_client.get_system_status()
            return self._format_system_status(status)

        return (
            "I don't have a tool for that request yet. "
            "For now, try asking, “How is the Pi doing?”"
        )

    def _requests_system_status(self, message: str) -> bool:
        """Determine whether a message requests system information."""

        return any(
            phrase in message
            for phrase in self.SYSTEM_STATUS_PHRASES
        )

    def _format_system_status(
        self,
        status: dict[str, Any],
    ) -> str:
        """Convert structured system data into a friendly response."""

        cpu = status["cpu"]
        memory = status["memory"]
        disk = status["disk"]

        uptime = self._format_uptime(status["uptime_seconds"])
        available_memory = self._bytes_to_gib(memory["available_bytes"])
        free_disk = self._bytes_to_gib(disk["free_bytes"])

        temperature = cpu.get("temperature_celsius")
        temperature_text = (
            f"{temperature:.1f}°C"
            if temperature is not None
            else "unavailable"
        )

        return (
            f"{status['hostname']} is online and looking healthy. "
            f"CPU usage is {cpu['usage_percent']:.1f}% at "
            f"{temperature_text}. "
            f"Memory usage is {memory['usage_percent']:.1f}%, with "
            f"{available_memory:.1f} GiB available. "
            f"Disk usage is {disk['usage_percent']:.1f}%, with "
            f"{free_disk:.1f} GiB free. "
            f"Uptime is {uptime}."
        )

    @staticmethod
    def _bytes_to_gib(byte_count: int) -> float:
        """Convert bytes to gibibytes."""

        return byte_count / (1024**3)

    @staticmethod
    def _format_uptime(total_seconds: int) -> str:
        """Format an uptime duration for conversational output."""

        days, remainder = divmod(total_seconds, 86_400)
        hours, remainder = divmod(remainder, 3_600)
        minutes, _ = divmod(remainder, 60)

        parts: list[str] = []

        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")

        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")

        if minutes or not parts:
            parts.append(
                f"{minutes} minute{'s' if minutes != 1 else ''}"
            )

        return ", ".join(parts)


async def main() -> None:
    """Run a single conversational Psydekik request."""

    async with ChappieMCPClient() as mcp_client:
        orchestrator = ChappieOrchestrator(mcp_client)

        message = input("You: ")
        response = await orchestrator.handle_message(message)

        print(f"Chappie: {response}")


if __name__ == "__main__":
    asyncio.run(main())
