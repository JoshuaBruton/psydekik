"""Local conversational brain for Chappie."""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from chappie.brain.context import ConversationContext
from chappie.brain.prompts import CHAPPIE_SYSTEM_PROMPT


@dataclass(frozen=True, slots=True)
class BrainResponse:
    """Result returned by Chappie's conversational brain."""

    text: str
    elapsed_seconds: float


class ChappieBrain:
    """Conversational interface to Chappie's local Ollama model."""

    def __init__(
        self,
        *,
        model: str = "llama3.2:1b-instruct-q3_K_M",
        base_url: str = "http://127.0.0.1:11434",
        context: ConversationContext | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.context = context or ConversationContext()

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(
                connect=5.0,
                read=120.0,
                write=10.0,
                pool=5.0,
            ),
        )

    async def respond(self, message: str) -> BrainResponse:
        """Generate a conversational response."""

        message = message.strip()

        if not message:
            raise ValueError("Message cannot be empty.")

        history = self.context.snapshot()

        messages = [
            {
                "role": "system",
                "content": CHAPPIE_SYSTEM_PROMPT,
            },
            *history,
            {
                "role": "user",
                "content": message,
            },
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "temperature": 0.25,
                "num_predict": 120,
                "num_ctx": 2048,
            },
        }

        started = time.perf_counter()

        response = await self._client.post(
            "/api/chat",
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

        elapsed = time.perf_counter() - started

        text = (
            data.get("message", {})
            .get("content", "")
            .strip()
        )

        if not text:
            raise RuntimeError(
                "Ollama returned an empty response."
            )

        self.context.add_user(message)
        self.context.add_assistant(text)

        return BrainResponse(
            text=text,
            elapsed_seconds=elapsed,
        )

    def remember_exchange(
        self,
        user_text: str,
        assistant_text: str,
    ) -> None:
        """Remember an exchange answered outside the language model."""

        self.context.add_user(user_text)
        self.context.add_assistant(assistant_text)

    def clear_context(self) -> None:
        """Forget the current short-term conversation."""

        self.context.clear()

    async def close(self) -> None:
        """Close the HTTP client."""

        await self._client.aclose()

    async def __aenter__(self) -> ChappieBrain:
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> None:
        await self.close()
