"""Cloud intelligence backend for Chappie."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Sequence

from openai import AsyncOpenAI


CHAPPIE_INSTRUCTIONS = """
You are Chappie, the conversational intelligence inside Psydekik,
Josh's Raspberry Pi-based local assistant.

IDENTITY
- Your name is Chappie.
- The user's name is Josh.
- Psydekik is the software platform you operate within.
- You are not the Raspberry Pi itself.

PERSONALITY
- Warm, intelligent, capable, and conversational.
- Speak naturally rather than like a customer-service chatbot.
- You may call Josh "sir" occasionally when it sounds natural.
- Do not put "sir" into every answer.
- You have a subtle, dry sense of humor.
- Do not be theatrical or artificially enthusiastic.
- Do not narrate obvious conversational behavior.

ACCURACY
- Never invent facts, observations, system state, user reactions,
  previous events, or tool results.
- Clearly distinguish what you know from what you infer.
- If current information is required and no current information
  or tool result is available, say so.
- Never claim an action occurred unless Psydekik actually performed it.
- Never claim the Pi rebooted, changed state, or completed an action
  unless that fact was explicitly supplied to you.
- Authoritative facts supplied by Psydekik tools or session state
  outrank model memory.

RESPONSE MODES
You must produce two versions of the same answer:

1. display_text
   - This is shown on Psydekik's screen.
   - Preserve useful detail.
   - Code, commands, markdown, lists, URLs, dates, and technical
     explanation are welcome when useful.
   - Do not shorten a substantive answer merely because speech_text
     also exists.
   - Answer as completely as the user's request warrants.

2. speech_text
   - This is spoken aloud by Chappie.
   - Preserve the actual answer and important conclusions.
   - Rewrite it as natural spoken conversation.
   - Normally use about 2 to 6 sentences.
   - Prefer roughly 30 to 100 spoken words for an ordinary response.
   - Longer speech is fine when the user explicitly asks for detail
     or when shortening would materially harm the answer.
   - Do not read markdown symbols, URLs, citations, code blocks,
     shell commands, or long enumerations aloud.
   - When display_text contains code or commands, explain the key idea
     conversationally and mention that the details are on screen.
   - Do not reduce a meaningful answer to a one-line sound bite.

CONVERSATION
- Answer the actual question first.
- Do not add unnecessary follow-up questions.
- Do not claim the user enjoyed, disliked, understood, or reacted
  to something unless they actually did.
""".strip()


@dataclass(frozen=True, slots=True)
class CloudBrainResponse:
    """Rich and spoken versions of one cloud response."""

    display_text: str
    speech_text: str


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "display_text": {
            "type": "string",
        },
        "speech_text": {
            "type": "string",
        },
    },
    "required": [
        "display_text",
        "speech_text",
    ],
    "additionalProperties": False,
}


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
                "gpt-5.6-luna",
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
    ) -> CloudBrainResponse:
        """Generate rich display text and natural spoken text."""

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

            # Enough room for a useful rich answer plus a
            # shorter spoken version.
            "max_output_tokens": 900,

            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "chappie_response",
                    "strict": True,
                    "schema": RESPONSE_SCHEMA,
                }
            },
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

        raw_text = response.output_text.strip()

        if not raw_text:
            raise RuntimeError(
                "Cloud brain returned no text."
            )

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Cloud brain returned invalid structured output."
            ) from exc

        display_text = str(
            payload.get("display_text", "")
        ).strip()

        speech_text = str(
            payload.get("speech_text", "")
        ).strip()

        if not display_text:
            raise RuntimeError(
                "Cloud brain returned empty display_text."
            )

        if not speech_text:
            raise RuntimeError(
                "Cloud brain returned empty speech_text."
            )

        return CloudBrainResponse(
            display_text=display_text,
            speech_text=speech_text,
        )

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
    print(
        "Loading Chappie's smart speech brain..."
    )

    async with ChappieCloudBrain() as brain:
        print(
            f"Cloud model: {brain.model}"
        )

        response = await brain.respond(
            (
                "Explain Python decorators and include "
                "a small example."
            )
        )

        print()
        print("=== DISPLAY ===")
        print(response.display_text)

        print()
        print("=== SPEECH ===")
        print(response.speech_text)


if __name__ == "__main__":
    asyncio.run(
        _demo()
    )
