"""Thread-safe state and voice runtime for Chappie's console presence."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import StrEnum
from queue import Empty, Queue, SimpleQueue
from threading import Event, Thread
from typing import Any, Callable


class ChappieMode(StrEnum):
    """Visible stages of one Chappie interaction."""

    STARTING = "Starting"
    IDLE = "Idle"
    LISTENING = "Listening"
    TRANSCRIBING = "Transcribing"
    THINKING = "Thinking"
    SPEAKING = "Speaking"
    ERROR = "Error"


@dataclass(frozen=True, slots=True)
class ChappieSnapshot:
    """One immutable update for the Chappie presence card."""

    mode: ChappieMode
    headline: str
    detail: str
    transcript: str = ""


class ChappieVoiceController:
    """Keep voice work off Tk's UI thread and publish safe updates."""

    def __init__(
        self,
        scheduler: Any,
        on_state: Callable[[ChappieSnapshot], None],
    ) -> None:
        self.scheduler = scheduler
        self.on_state = on_state
        self._commands: Queue[str | None] = Queue()
        self._events: SimpleQueue[ChappieSnapshot] = SimpleQueue()
        self._ready = Event()
        self._busy = Event()
        self._started = False

    def start(self) -> None:
        """Start the persistent voice runtime and UI event pump."""

        if self._started:
            return

        self._started = True
        self._drain_events()
        Thread(
            target=self._thread_main,
            name="chappie-console-voice",
            daemon=True,
        ).start()

    def request_turn(self) -> None:
        """Queue one microphone-driven conversational turn."""

        if not self._ready.is_set():
            self._publish(
                ChappieMode.STARTING,
                "Chappie's voice is warming up.",
                "The first startup loads the local speech models.",
            )
            return

        if self._busy.is_set():
            return

        self._busy.set()
        self._commands.put("talk")

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._runtime())
        except Exception as exc:
            self._ready.clear()
            self._busy.clear()
            self._publish_error(exc)

    async def _runtime(self) -> None:
        # Heavy imports and model construction happen on the worker.
        from chappie.mcp_client import ChappieMCPClient
        from chappie.orchestrator import ChappieOrchestrator
        from chappie.voice.listen import (
            CONVERSATION_END_PHRASES,
            DEFAULT_AUDIO_PATH,
            FOLLOWUP_TIMEOUT_SECONDS,
            INITIAL_COMMAND_TIMEOUT_SECONDS,
            SHUTDOWN_PHRASES,
            VoiceListener,
            normalize_message,
        )
        from chappie.voice.tts import PiperTTS

        self._publish(
            ChappieMode.STARTING,
            "Bringing Chappie online...",
            "Loading local speech and conversation services.",
        )

        listener = VoiceListener(DEFAULT_AUDIO_PATH)
        tts = PiperTTS()
        tts.warm_up()

        async with ChappieMCPClient() as mcp_client:
            orchestrator = ChappieOrchestrator(mcp_client)
            self._ready.set()
            self._publish_idle("Voice, memory, and MCP are online.")

            try:
                while True:
                    command = await asyncio.to_thread(
                        self._commands.get
                    )

                    if command is None:
                        break

                    if command == "talk":
                        await self._run_conversation(
                            listener=listener,
                            orchestrator=orchestrator,
                            tts=tts,
                            initial_timeout_seconds=(
                                INITIAL_COMMAND_TIMEOUT_SECONDS
                            ),
                            followup_timeout_seconds=(
                                FOLLOWUP_TIMEOUT_SECONDS
                            ),
                            end_phrases=(
                                CONVERSATION_END_PHRASES
                                | SHUTDOWN_PHRASES
                            ),
                            normalize=normalize_message,
                        )
            finally:
                await orchestrator.close()

    async def _run_conversation(
        self,
        *,
        listener: Any,
        orchestrator: Any,
        tts: Any,
        initial_timeout_seconds: float,
        followup_timeout_seconds: float,
        end_phrases: set[str],
        normalize: Callable[[str], str],
    ) -> None:
        """Run turns until silence or an explicit ending phrase."""

        transcript = ""
        followup = False

        try:
            while True:
                if followup:
                    headline = "Anything else, sir?"
                    detail = (
                        "Listening for a follow-up. Say “that's all” "
                        "when we're finished."
                    )
                    timeout_seconds = followup_timeout_seconds
                else:
                    headline = "I'm listening..."
                    detail = "Speak naturally. I'll stop when you finish."
                    timeout_seconds = initial_timeout_seconds

                self._publish(
                    ChappieMode.LISTENING,
                    headline,
                    detail,
                    transcript=transcript if followup else "",
                )

                original_timeout = (
                    listener.recorder.speech_timeout_seconds
                )
                listener.recorder.speech_timeout_seconds = (
                    timeout_seconds
                )

                try:
                    try:
                        recorded_path = listener.recorder.record(
                            output_path=listener.audio_path
                        )
                    except TimeoutError:
                        recorded_path = None
                finally:
                    listener.recorder.speech_timeout_seconds = (
                        original_timeout
                    )

                if recorded_path is None:
                    if followup:
                        detail = (
                            "Conversation complete. Tap Talk whenever "
                            "you need me."
                        )
                    else:
                        detail = (
                            "I didn't hear a command. Tap Talk to try "
                            "again."
                        )

                    self._publish_idle(
                        detail,
                        transcript=transcript,
                    )
                    return

                self._publish(
                    ChappieMode.TRANSCRIBING,
                    "Putting words to that...",
                    "Local speech recognition is processing the recording.",
                )
                transcript = listener.stt.transcribe(recorded_path)

                if not transcript:
                    self._publish_idle(
                        "I couldn't make that out. Tap Talk to try again."
                    )
                    return

                if normalize(transcript) in end_phrases:
                    self._publish_idle(
                        "Conversation complete. I'll be right here.",
                        transcript=transcript,
                    )
                    return

                self._publish(
                    ChappieMode.THINKING,
                    "Working on it...",
                    "Chappie is choosing the right tool and response.",
                    transcript=transcript,
                )
                response = await orchestrator.handle_voice_message(
                    transcript
                )

                self._publish(
                    ChappieMode.SPEAKING,
                    response.display_text,
                    "Speaking through the Pi now.",
                    transcript=transcript,
                )
                tts.speak(response.speech_text)
                followup = True
        except Exception as exc:
            self._publish_error(exc, transcript=transcript)
        finally:
            self._busy.clear()

    def _publish_idle(
        self,
        detail: str,
        *,
        transcript: str = "",
    ) -> None:
        self._publish(
            ChappieMode.IDLE,
            "Ready when you are, sir.",
            detail,
            transcript=transcript,
        )

    def _publish_error(
        self,
        error: Exception,
        *,
        transcript: str = "",
    ) -> None:
        self._publish(
            ChappieMode.ERROR,
            "I hit a snag.",
            str(error),
            transcript=transcript,
        )

    def _publish(
        self,
        mode: ChappieMode,
        headline: str,
        detail: str,
        *,
        transcript: str = "",
    ) -> None:
        self._events.put(
            ChappieSnapshot(
                mode=mode,
                headline=headline,
                detail=detail,
                transcript=transcript,
            )
        )

    def _drain_events(self) -> None:
        while True:
            try:
                snapshot = self._events.get_nowait()
            except Empty:
                break

            self.on_state(snapshot)

        self.scheduler.after(100, self._drain_events)
