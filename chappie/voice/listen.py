"""Persistent wake-word-driven voice session for Chappie."""

from __future__ import annotations

import asyncio
from pathlib import Path

from chappie.mcp_client import ChappieMCPClient
from chappie.orchestrator import ChappieOrchestrator
from chappie.voice.recorder import VoiceRecorder
from chappie.voice.stt import SpeechToText
from chappie.voice.tts import PiperTTS
from chappie.voice.wake_word import ChappieWakeWord


DEFAULT_AUDIO_PATH = Path(
    "/tmp/psydekik-command.wav"
)


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
    ) -> str:
        """Record one command and return its transcription."""

        print()
        print("Listening for command...")

        recorded_path = self.recorder.record(
            output_path=self.audio_path
        )

        if recorded_path is None:
            recorded_path = self.audio_path

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


async def main() -> None:
    """Run Chappie's wake-word-driven voice session."""

    print()
    print("Starting Chappie...")

    #
    # Keep the heavy components alive for the
    # lifetime of the process.
    #
    listener = VoiceListener()

    tts = PiperTTS()
    tts.warm_up()

    wake_word = ChappieWakeWord()

    #
    # Generate/cache the short wake acknowledgment.
    #
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
            while True:
                #
                # IDLE STATE
                #
                # Nothing enters STT or the brain until
                # the wake phrase has been detected.
                #
                wake_word.wait()

                #
                # ACKNOWLEDGMENT
                #
                print('Chappie: "Sir?"')

                tts.play(
                    acknowledgment_path
                )

                #
                # COMMAND STATE
                #
                message = listener.listen_once()

                if not message:
                    print(
                        "No command received. "
                        "Returning to sleep."
                    )
                    continue

                normalized = (
                    message
                    .strip()
                    .lower()
                )

                #
                # Spoken shutdown command.
                #
                if normalized in {
                    "exit",
                    "quit",
                    "goodbye chappie",
                    "goodbye chappy",
                    "go offline chappie",
                    "go offline chappy",
                }:
                    print(
                        "Voice session ended."
                    )
                    break

                print(
                    "Thinking..."
                )

                response = (
                    await orchestrator.handle_voice_message(
                        message
                    )
                )

                #
                # Rich response for the screen.
                #
                print(
                    f"Chappie: "
                    f"{response.display_text}"
                )

                #
                # Natural conversational response.
                #
                print(
                    f"Speaking: "
                    f"{response.speech_text}"
                )

                tts.speak(
                    response.speech_text
                )

                #
                # Loop naturally returns to wake-word
                # listening after speech completes.
                #

        except KeyboardInterrupt:
            print()
            print(
                "Voice session stopped."
            )

        finally:
            await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(
        main()
    )
