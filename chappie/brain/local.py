from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Final

import httpx


class SystemIntent(StrEnum):
    OVERVIEW = "overview"
    CPU = "cpu"
    TEMPERATURE = "temperature"
    MEMORY = "memory"
    STORAGE = "storage"
    UPTIME = "uptime"
    UNKNOWN = "unknown"


VALID_INTENTS: Final[set[str]] = {
    intent.value
    for intent in SystemIntent
}


SYSTEM_PROMPT: Final[str] = """
You are Chappie's Raspberry Pi system-intent classifier.

Your ONLY job is to choose one intent from this exact list:

overview
cpu
temperature
memory
storage
uptime
unknown

INTENT DEFINITIONS

overview:
General system health, overall Pi status, whether anything
looks wrong, strange, unhealthy, sketchy, or concerning.

cpu:
CPU usage, processor load, CPU activity, processor utilization.

temperature:
Heat, hot, cold, temperature, thermals, overheating, degrees.

memory:
RAM, available memory, used memory, memory pressure.

storage:
Disk space, free storage, drive capacity, room left,
space remaining, available disk space.

uptime:
How long the Pi has been running, how long it has been up,
or when it last restarted.

unknown:
Only use this if the request does NOT relate to any category above.

EXAMPLES

User: Is the Pi getting hot?
Answer: temperature

User: Is she running a little warm?
Answer: temperature

User: What's the CPU doing?
Answer: cpu

User: How hard is the processor working?
Answer: cpu

User: How much RAM is left?
Answer: memory

User: What about memory?
Answer: memory

User: How much room have I got left?
Answer: storage

User: Am I running out of space?
Answer: storage

User: How long has it been up?
Answer: uptime

User: How long has she been running?
Answer: uptime

User: Anything looking sketchy?
Answer: overview

User: Does anything look weird?
Answer: overview

IMPORTANT RULES

- "hot", "warm", "heat", or "thermal" means temperature.
- Do NOT classify heat questions as cpu.
- "room left" or "space left" means storage.
- vague questions about whether the Pi looks healthy mean overview.
- use unknown only when none of the six system intents applies.
- output exactly ONE lowercase intent word.
- output no punctuation.
- output no explanation.
""".strip()


class ChappieBrain:
    def __init__(
        self,
        *,
        model: str = "qwen3:0.6b",
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 15.0,
        keep_alive: str = "30m",
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.keep_alive = keep_alive

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "ChappieBrain":
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        traceback,
    ) -> None:
        await self.close()

    async def classify_system_intent(
        self,
        message: str,
        *,
        context: str | None = None,
    ) -> SystemIntent:
        user_content = f"User request:\n{message.strip()}"

        if context:
            user_content += (
                "\n\nConversation context:\n"
                f"{context.strip()}"
            )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            "think": False,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": 0,
                "num_predict": 64,
            },
        }

        try:
            response = await self._client.post(
                "/api/chat",
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return SystemIntent.UNKNOWN

        data = response.json()

        raw_content = (
            data
            .get("message", {})
            .get("content", "")
        )

        intent_name = self._normalize_intent(
            raw_content
        )

        return SystemIntent(intent_name)

    @staticmethod
    def _normalize_intent(
        raw_content: str,
    ) -> str:
        cleaned = (
            raw_content
            .strip()
            .lower()
            .replace("`", "")
            .replace(".", "")
            .replace(",", "")
            .replace('"', "")
            .replace("'", "")
        )

        first_word = (
            cleaned.split()[0]
            if cleaned
            else ""
        )

        if first_word in VALID_INTENTS:
            return first_word

        return SystemIntent.UNKNOWN.value


async def _main() -> None:
    print("Starting Chappie's local brain...")
    print()

    tests = (
        (
            "Is the Pi getting a little hot?",
            None,
        ),
        (
            "How much room have I got left on this thing?",
            "The user is talking about the Raspberry Pi.",
        ),
        (
            "Anything looking sketchy?",
            "The user is asking about the Raspberry Pi system.",
        ),
    )

    async with ChappieBrain() as brain:
        for message, context in tests:
            start = asyncio.get_running_loop().time()

            intent = await brain.classify_system_intent(
                message,
                context=context,
            )

            elapsed = (
                asyncio.get_running_loop().time()
                - start
            )

            print(f"Request: {message}")
            print(f"Intent:  {intent.value}")
            print(f"Time:    {elapsed:.2f}s")
            print()


if __name__ == "__main__":
    asyncio.run(_main())
