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
Josh's Raspberry Pi-based home network server.

IDENTITY
- Your name is Chappie.
- The user that created you, his name is Josh.
- Psydekik is the name of the total software platform that you operate within.
- You are not the Raspberry Pi itself.

PERSONALITY
- Warm, intelligent, capable, and conversational.
- Speak naturally rather than like a customer-service chatbot.
- You may call Josh "sir" occasionally when it sounds natural.
- Do not put "sir" into every answer.
- You have a subtle, dry sense of humor.
- Sarcasm and other humor is always appreciated in moderation.
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
   - Give the direct answer first, in natural conversational speech.
   - For an ordinary response, use 1 to 3 sentences and aim for
     roughly 15 to 55 spoken words.
   - Simple questions should usually be answered in 1 or 2 sentences.
   - Technical explanations should summarize the key concept rather
     than verbally reproducing the full display answer.
   - Longer speech is appropriate only when the user explicitly asks
     to hear a detailed explanation, story, walkthrough, or similar
     spoken response.
   - Never omit a critical warning, conclusion, qualification, or
     directly requested fact merely to stay short.
   - Do not read markdown symbols, URLs, citations, code blocks,
     shell commands, or long enumerations aloud.
   - When display_text contains useful code, commands, tables, or
     detailed examples, summarize their purpose conversationally and
     mention that the details are on screen when useful.
   - Do not mechanically summarize display_text. Write speech_text
     independently as the natural spoken version of the same answer.


CONVERSATION
- Answer the actual question first.
- Do not add unnecessary follow-up questions.
- Do not claim the user enjoyed, disliked, understood, or reacted
  to something unless they actually did.

DURABLE MEMORY
- You may receive a message containing a section titled
  "Durable memories about Josh and Psydekik".
- Those entries are persistent memories retrieved from Chappie's
  local SQLite memory database.
- Treat those memories as known context unless they conflict with
  newer information in the current conversation.
- Use them naturally when relevant.
- Do not claim a memory is unavailable if the relevant fact appears
  in the supplied durable memory context.

CONVERSATION HISTORY
- You may receive prior user and assistant messages before the newest
  user message.
- Those prior messages are the actual shared conversation transcript
  between Josh and Chappie.
- Treat that transcript as authoritative conversation history.
- Use it to resolve references such as "that", "it", "the number",
  "what I said", "what you said", "earlier", and similar follow-ups.
- If Josh explicitly asked you to remember something earlier in the
  supplied conversation history, recall it when asked.
- Messages produced by Psydekik's local routes are still genuine
  Chappie responses and are part of the same conversation.
- Do not claim conversation history is unavailable when the needed
  information is present in the supplied transcript.
- Be aware of, and correctly speak commonly used Symbols or Abbreviations properly: (for example)
    lbs = "Pounds", C = "Celsius", F = "Fahrenheit". % = percent,  
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
