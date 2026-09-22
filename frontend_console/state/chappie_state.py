"""Thread-safe state and voice runtime for Chappie's console presence."""

from __future__ import annotations

import atexit
import asyncio
from dataclasses import dataclass
from enum import StrEnum
from queue import Empty, SimpleQueue
import re
from threading import Event, Thread
from typing import Any, Callable


class ChappieMode(StrEnum):
    """Visible stages of one Chappie interaction."""

    STARTING = "Starting"
    SLEEPING = "Sleeping"
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
        self._events: SimpleQueue[ChappieSnapshot] = SimpleQueue()
        self._ready = Event()
        self._busy = Event()
        self._stop_requested = Event()
        self._wake_interrupt = Event()
        self._manual_request = Event()
        self._started = False
        atexit.register(self.stop)

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
        self._manual_request.set()
        self._wake_interrupt.set()

    def stop(self) -> None:
        """Request a graceful worker shutdown without blocking Tk."""

        self._ready.clear()
        self._stop_requested.set()
        self._wake_interrupt.set()

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
        from chappie.voice.wake_word import ChappieWakeWord

        self._publish(
            ChappieMode.STARTING,
            "Bringing Chappie online...",
            "Loading local speech and conversation services.",
        )

        listener = VoiceListener(DEFAULT_AUDIO_PATH)
        tts = PiperTTS()
        tts.warm_up()
        wake_word = ChappieWakeWord()
        acknowledgment_path = tts.cache_acknowledgment()

        async with ChappieMCPClient() as mcp_client:
            orchestrator = ChappieOrchestrator(mcp_client)
            self._ready.set()

            try:
                while not self._stop_requested.is_set():
                    self._wake_interrupt.clear()
                    self._publish_sleeping(
                        "Voice, memory, wake word, and MCP are online."
                    )

                    wake_phrase = wake_word.wait(
                        self._wake_interrupt
                    )

                    if self._stop_requested.is_set():
                        break

                    manual_request = (
                        self._manual_request.is_set()
                    )
                    self._manual_request.clear()

                    if not wake_phrase and not manual_request:
                        continue

                    self._busy.set()

                    if wake_phrase:
                        self._publish(
                            ChappieMode.LISTENING,
                            "Yes, sir?",
                            "Wake word detected. Preparing to listen.",
                        )
                        tts.play(acknowledgment_path)

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
                self._ready.clear()
                self._wake_interrupt.set()
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

                print(f'STT transcript: "{transcript}"')

                if not transcript:
                    self._publish_idle(
                        "I couldn't make that out. Tap Talk to try again."
                    )
                    return

                if self._is_end_phrase(
                    transcript,
                    end_phrases=end_phrases,
                    normalize=normalize,
                ):
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

    @staticmethod
    def _is_end_phrase(
        transcript: str,
        *,
        end_phrases: set[str],
        normalize: Callable[[str], str],
    ) -> bool:
        """Recognize natural, standalone conversation-ending phrases."""

        extra_phrases = {
            "thanks",
            "thank you",
            "that's it",
            "thats it",
            "that is all",
            "nothing else",
            "no thanks",
            "no thank you",
            "we're done",
            "were done",
            "go to sleep",
            "good night",
            "goodnight",
        }

        def clean(value: str) -> str:
            cleaned = normalize(value).replace("’", "'")
            cleaned = re.sub(r"[^a-z0-9\s]", "", cleaned)
            return " ".join(cleaned.split())

        phrase = clean(transcript)

        polite_prefixes = (
            "okay ",
            "ok ",
            "alright ",
            "all right ",
            "well ",
        )
        polite_suffixes = (
            " chappie",
            " chappy",
            " please",
            " sir",
        )

        changed = True

        while changed:
            changed = False

            for prefix in polite_prefixes:
                if phrase.startswith(prefix):
                    phrase = phrase[len(prefix):].strip()
                    changed = True

            for suffix in polite_suffixes:
                if phrase.endswith(suffix):
                    phrase = phrase[:-len(suffix)].strip()
                    changed = True

        accepted = {
            clean(candidate)
            for candidate in end_phrases | extra_phrases
        }

        return phrase in accepted

    def _publish_sleeping(
        self,
        detail: str,
        *,
        transcript: str = "",
    ) -> None:
        self._publish(
            ChappieMode.SLEEPING,
            'Sleeping — say "Hey Chappie."',
            detail,
            transcript=transcript,
        )

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
