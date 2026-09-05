"""Persistent conversational voice session for Chappie."""

from __future__ import annotations

import asyncio
from pathlib import Path

from chappie.mcp_client import ChappieMCPClient
from chappie.orchestrator import ChappieOrchestrator
from chappie.voice.recorder import VoiceRecorder
from chappie.voice.shutdown import shutdown
from chappie.voice.stt import SpeechToText
from chappie.voice.tts import PiperTTS
from chappie.voice.wake_word import ChappieWakeWord


DEFAULT_AUDIO_PATH = Path(
    "/tmp/psydekik-command.wav"
)

INITIAL_COMMAND_TIMEOUT_SECONDS = 8.0
FOLLOWUP_TIMEOUT_SECONDS = 10.0


CONVERSATION_END_PHRASES = {
    "that's all",
    "thats all",
    "thanks chappie",
    "thanks chappy",
    "thank you chappie",
    "thank you chappy",
    "never mind",
    "nevermind",
    "go back to sleep",
    "back to sleep",
    "you can go back to sleep",
}


SHUTDOWN_PHRASES = {
    "exit",
    "quit",
    "goodbye chappie",
    "goodbye chappy",
    "go offline chappie",
    "go offline chappy",
    "shut down chappie",
    "shutdown chappie",
    "shut down chappy",
    "shutdown chappy",
}


class VoiceListener:
    """Record and transcribe spoken commands."""

    def __init__(
        self,
        audio_path: Path = DEFAULT_AUDIO_PATH,
    ) -> None:
        self.audio_path = audio_path
        self.recorder = VoiceRecorder()
        self.stt = SpeechToText()

    def listen_once(
        self,
        *,
        speech_timeout_seconds: float | None = None,
        followup: bool = False,
    ) -> str:
        """Record one utterance and return its transcription."""

        print()

        if followup:
            print("Listening for follow-up...")
        else:
            print("Listening for command...")

        original_timeout = (
            self.recorder.speech_timeout_seconds
        )

        if speech_timeout_seconds is not None:
            self.recorder.speech_timeout_seconds = (
                speech_timeout_seconds
            )

        try:
            try:
                recorded_path = self.recorder.record(
                    output_path=self.audio_path
                )
            except TimeoutError:
                return ""

        finally:
            self.recorder.speech_timeout_seconds = (
                original_timeout
            )

        if recorded_path is None:
            if shutdown.requested:
                return ""

            return ""

        if shutdown.requested:
            return ""

        print("Transcribing...")

        text = self.stt.transcribe(
            recorded_path
        )

        if text:
            print(
                f'You said: "{text}"'
            )
        else:
            print(
                "No speech was recognized."
            )

        return text


def normalize_message(
    message: str,
) -> str:
    """Normalize spoken text for local control phrases."""

    return (
        message
        .strip()
        .casefold()
    )


async def handle_turn(
    *,
    orchestrator: ChappieOrchestrator,
    tts: PiperTTS,
    message: str,
) -> None:
    """Process and speak one conversational turn."""

    print(
        "Thinking..."
    )

    response = (
        await orchestrator.handle_voice_message(
            message
        )
    )

    print(
        f"Chappie: "
        f"{response.display_text}"
    )

    print(
        f"Speaking: "
        f"{response.speech_text}"
    )

    tts.speak(
        response.speech_text
    )


async def main() -> None:
    """Run Chappie's wake-word-driven conversation loop."""

    shutdown.install_signal_handlers()

    print()
    print("Starting Chappie...")

    #
    # Heavy components stay alive for the lifetime
    # of the process.
    #
    listener = VoiceListener()

    tts = PiperTTS()
    tts.warm_up()

    wake_word = ChappieWakeWord()

    acknowledgment_path = (
        tts.cache_acknowledgment()
    )

    print(
        "Chappie's voice is ready."
    )

    async with ChappieMCPClient() as mcp_client:
        orchestrator = ChappieOrchestrator(
            mcp_client
        )

        print(
            "Chappie is online."
        )

        try:
            while not shutdown.requested:

                # ==========================================
                # SLEEP STATE
                # ==========================================

                wake_word.wait()

                if shutdown.requested:
                    break

                print(
                    'Chappie: "Sir?"'
                )

                tts.play(
                    acknowledgment_path
                )

                if shutdown.requested:
                    break

                # ==========================================
                # FIRST CONVERSATION TURN
                # ==========================================

                message = listener.listen_once(
                    speech_timeout_seconds=(
                        INITIAL_COMMAND_TIMEOUT_SECONDS
                    ),
                    followup=False,
                )

                if shutdown.requested:
                    break

                if not message:
                    print(
                        "No command received. "
                        "Returning to sleep."
                    )
                    continue

                # ==========================================
                # ACTIVE CONVERSATION
                # ==========================================

                while not shutdown.requested:
                    normalized = normalize_message(
                        message
                    )

                    #
                    # Shut down the entire runtime.
                    #
                    if normalized in SHUTDOWN_PHRASES:
                        print(
                            "Voice session ended."
                        )
                        shutdown.request()
                        break

                    #
                    # End only the current conversation.
                    #
                    if normalized in CONVERSATION_END_PHRASES:
                        print(
                            "Conversation ended. "
                            "Returning to sleep."
                        )
                        break

                    await handle_turn(
                        orchestrator=orchestrator,
                        tts=tts,
                        message=message,
                    )

                    if shutdown.requested:
                        break

                    # ======================================
                    # FOLLOW-UP WINDOW
                    # ======================================

                    message = listener.listen_once(
                        speech_timeout_seconds=(
                            FOLLOWUP_TIMEOUT_SECONDS
                        ),
                        followup=True,
                    )

                    if shutdown.requested:
                        break

                    if not message:
                        print(
                            "Conversation idle. "
                            "Returning to sleep."
                        )
                        break

                #
                # Inner conversation loop has ended.
                # Outer loop returns to wake-word mode.
                #

        except KeyboardInterrupt:
            print()
            print(
                "Voice session stopped."
            )

        finally:
            try:
                await orchestrator.close()
            except asyncio.CancelledError:
                pass

            print(
                "Chappie is offline."
            )


if __name__ == "__main__":
    try:
        asyncio.run(
            main()
        )
    except KeyboardInterrupt:
        pass
