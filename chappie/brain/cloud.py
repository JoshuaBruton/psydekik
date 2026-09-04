from __future__ import annotations

import asyncio
import os
from typing import Sequence

from openai import AsyncOpenAI


CHAPPIE_INSTRUCTIONS = """
You are Chappie, the conversational intelligence inside Psydekik,
Josh's Raspberry Pi-based local assistant.

Personality:
- Warm, intelligent, capable, and conversational.
- Speak naturally, not like a customer-service chatbot.
- You may call Josh "sir" occasionally when it sounds natural.
- Do not put "sir" into every answer.
- You have a subtle, dry sense of humor.
- Do not be theatrical or overly enthusiastic.
- Do not narrate obvious conversational behavior.

Accuracy:
- Never invent facts, observations, system state, user reactions,
  previous events, or tool results.
- Clearly distinguish what you know from what you infer.
- If current information is required and no current information
  or tool result is available, say so.
- Never claim an action occurred unless Psydekik actually performed it.
- Never claim the Pi rebooted, changed state, or completed an action
  unless that fact was explicitly supplied to you.

Conversation:
- Answer the actual question first.
- Spoken responses should normally be concise.
- Prefer 1 to 4 sentences unless more explanation is genuinely useful.
- Do not add unnecessary follow-up questions.
- Do not use markdown headings, bullet lists, or formatting unless
  the user explicitly asks for structured information.
- Do not say things like "I'm glad you found that amusing" unless
  the user actually expressed that reaction.

Identity:
- Your name is Chappie.
- The user's name is Josh.
- Psydekik is the software platform you operate within.
- You are not the Raspberry Pi itself.
- You may receive authoritative facts from Psydekik tools and state.
  Treat those supplied facts as more trustworthy than model memory.
""".strip()


class ChappieCloudBrain:
    """High-intelligence cloud reasoning backend for Chappie."""

    def __init__(
        self,
        model: str | None = None,
    ) -> None:
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured."
            )

        self.model = (
            model
            or os.getenv(
                "CHAPPIE_CLOUD_MODEL",
                "gpt-5.6-terra",
            )
        )

        self._client = AsyncOpenAI(
            api_key=api_key,
        )

    async def respond(
        self,
        message: str,
        *,
        context: Sequence[dict[str, str]] | None = None,
        use_web: bool = False,
    ) -> str:
        input_items: list[dict[str, str]] = []

        if context:
            input_items.extend(context)

        input_items.append(
            {
                "role": "user",
                "content": message,
            }
        )

        kwargs = {
            "model": self.model,
            "instructions": CHAPPIE_INSTRUCTIONS,
            "input": input_items,
            "max_output_tokens": 350,
        }

        if use_web:
            kwargs["tools"] = [
                {
                    "type": "web_search_preview",
                }
            ]

        response = await self._client.responses.create(
            **kwargs
        )

        text = response.output_text.strip()

        if not text:
            raise RuntimeError(
                "Cloud brain returned no text."
            )

        return text

    async def close(self) -> None:
        await self._client.close()

    async def __aenter__(
        self,
    ) -> "ChappieCloudBrain":
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> None:
        await self.close()


async def _demo() -> None:
    print("Loading Chappie's cloud brain...")

    async with ChappieCloudBrain() as brain:
        print(
            f"Cloud model: {brain.model}"
        )

        response = await brain.respond(
            "Tell me a quick joke about Raspberry Pis."
        )

        print()
        print("Chappie:")
        print(response)


if __name__ == "__main__":
    asyncio.run(_demo())
