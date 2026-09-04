from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import sherpa_onnx
import soundfile as sf


DEFAULT_MODEL_DIR = (
    Path.home()
    / "Mainframe/psydekik/voice_lab/models"
    / "vits-piper-en_US-libritts_r-medium"
)

DEFAULT_CACHE_DIR = (
    Path.home()
    / ".cache/psydekik/tts/piper-sid300"
)

CHAPPIE_SPEAKER_ID = 300
CHAPPIE_SPEED = 1.0
CHAPPIE_THREADS = 2


class PiperTTS:
    """Generate and play Chappie's speech locally with Piper/VITS."""

    def __init__(
        self,
        model_dir: Path | None = None,
        cache_dir: Path | None = None,
        playback_device: str | None = None,
        speaker_id: int = CHAPPIE_SPEAKER_ID,
        speed: float = CHAPPIE_SPEED,
        num_threads: int = CHAPPIE_THREADS,
    ) -> None:
        configured_model_dir = os.getenv(
            "PSYDEKIK_TTS_MODEL_DIR"
        )

        configured_cache_dir = os.getenv(
            "PSYDEKIK_TTS_CACHE_DIR"
        )

        configured_playback_device = os.getenv(
            "PSYDEKIK_AUDIO_OUTPUT"
        )

        self.model_dir = (
            model_dir
            or (
                Path(
                    configured_model_dir
                ).expanduser()
                if configured_model_dir
                else DEFAULT_MODEL_DIR
            )
        )

        self.cache_dir = (
            cache_dir
            or (
                Path(
                    configured_cache_dir
                ).expanduser()
                if configured_cache_dir
                else DEFAULT_CACHE_DIR
            )
        )

        self.playback_device = (
            playback_device
            if playback_device is not None
            else configured_playback_device
        )

        self.speaker_id = speaker_id
        self.speed = speed
        self.num_threads = num_threads

        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._validate_model_files()

        # Created lazily or explicitly through warm_up().
        self._tts: sherpa_onnx.OfflineTts | None = None

    def _validate_model_files(
        self,
    ) -> None:
        """Confirm that all required Piper/VITS files exist."""

        required_paths = (
            self.model_dir
            / "en_US-libritts_r-medium.onnx",
            self.model_dir
            / "tokens.txt",
            self.model_dir
            / "espeak-ng-data",
        )

        missing_paths = [
            path
            for path in required_paths
            if not path.exists()
        ]

        if missing_paths:
            missing = ", ".join(
                str(path)
                for path in missing_paths
            )

            raise FileNotFoundError(
                "Missing Piper model files: "
                f"{missing}"
            )

    def _create_engine(
        self,
    ) -> sherpa_onnx.OfflineTts:
        """Load Piper/VITS into the Sherpa-ONNX runtime."""

        config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=(
                    sherpa_onnx.OfflineTtsVitsModelConfig(
                        model=str(
                            self.model_dir
                            / "en_US-libritts_r-medium.onnx"
                        ),
                        tokens=str(
                            self.model_dir
                            / "tokens.txt"
                        ),
                        data_dir=str(
                            self.model_dir
                            / "espeak-ng-data"
                        ),
                    )
                ),
                provider="cpu",
                num_threads=self.num_threads,
                debug=False,
            ),
            max_num_sentences=1,
        )

        if not config.validate():
            raise RuntimeError(
                "Piper TTS configuration is invalid."
            )

        return sherpa_onnx.OfflineTts(
            config
        )

    def _get_engine(
        self,
    ) -> sherpa_onnx.OfflineTts:
        """Return the persistent Piper engine."""

        if self._tts is None:
            self._tts = self._create_engine()

        return self._tts

    def warm_up(
        self,
    ) -> None:
        """Load Chappie's voice before live interaction."""

        if self._tts is not None:
            return

        print(
            "Loading Chappie's voice..."
        )

        start = time.perf_counter()

        self._tts = self._create_engine()

        elapsed = (
            time.perf_counter()
            - start
        )

        print(
            f"Voice ready in {elapsed:.2f}s."
        )

    def synthesize(
        self,
        text: str,
    ) -> Path:
        """Generate speech and return its cached WAV path."""

        normalized_text = text.strip()

        if not normalized_text:
            raise ValueError(
                "Cannot synthesize empty text."
            )

        output_path = self._cache_path(
            normalized_text
        )

        if output_path.exists():
            return output_path

        audio = self._get_engine().generate(
            normalized_text,
            sid=self.speaker_id,
            speed=self.speed,
        )

        if len(audio.samples) == 0:
            raise RuntimeError(
                "Piper generated no audio samples."
            )

        self._write_cache(
            output_path,
            audio.samples,
            audio.sample_rate,
        )

        return output_path

    def _write_cache(
        self,
        output_path: Path,
        samples,
        sample_rate: int,
    ) -> None:
        """Safely write generated speech to the cache."""

        temporary_path = (
            output_path.with_suffix(
                ".temporary.wav"
            )
        )

        sf.write(
            temporary_path,
            samples,
            samplerate=sample_rate,
            subtype="PCM_16",
        )

        temporary_path.replace(
            output_path
        )

    def play(
        self,
        audio_path: Path,
    ) -> None:
        """Play an existing WAV file through ALSA."""

        command = [
            "aplay",
            "--quiet",
        ]

        if self.playback_device:
            command.extend(
                [
                    "-D",
                    self.playback_device,
                ]
            )

        command.append(
            str(audio_path)
        )

        subprocess.run(
            command,
            check=True,
        )

    def speak_pipelined(
        self,
        text: str,
    ) -> Path:
        """
        Synthesize the response queue in one worker while
        playback consumes completed sentences in order.

        One worker owns the Sherpa TTS engine so that it is
        never accessed concurrently from Python.
        """

        chunks = self._split_text(
            text
        )

        if not chunks:
            raise ValueError(
                "Cannot speak empty text."
            )

        start_time = time.perf_counter()

        last_audio_path: Path | None = None

        print(
            f"TTS pipeline: "
            f"{len(chunks)} sentence(s)"
        )

        with ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="chappie-tts",
        ) as executor:
            futures = [
                executor.submit(
                    self.synthesize,
                    chunk,
                )
                for chunk in chunks
            ]

            for index, (
                chunk,
                future,
            ) in enumerate(
                zip(
                    chunks,
                    futures,
                ),
                start=1,
            ):
                wait_start = (
                    time.perf_counter()
                )

                audio_path = future.result()

                wait_time = (
                    time.perf_counter()
                    - wait_start
                )

                elapsed = (
                    time.perf_counter()
                    - start_time
                )

                if index == 1:
                    print(
                        "First TTS sentence "
                        "ready in "
                        f"{elapsed:.2f}s."
                    )

                print(
                    f"TTS sentence "
                    f"{index}/{len(chunks)} "
                    f"ready "
                    f"(playback wait "
                    f"{wait_time:.2f}s):"
                )

                print(
                    f"  {chunk}"
                )

                self.play(
                    audio_path
                )

                last_audio_path = (
                    audio_path
                )

        if last_audio_path is None:
            raise RuntimeError(
                "No TTS audio was generated."
            )

        total_elapsed = (
            time.perf_counter()
            - start_time
        )

        print(
            "TTS interaction completed in "
            f"{total_elapsed:.2f}s."
        )

        return last_audio_path

    def _split_text(
        self,
        text: str,
    ) -> list[str]:
        """Split speech into sentence-sized chunks."""

        normalized_text = text.strip()

        if not normalized_text:
            return []

        chunks = re.split(
            r"(?<=[.!?])\s+",
            normalized_text,
        )

        return [
            chunk.strip()
            for chunk in chunks
            if chunk.strip()
        ]

    def speak(
        self,
        text: str,
    ) -> Path:
        """Speak using sentence-level synthesis pipelining."""

        return self.speak_pipelined(
            text
        )

    def cache_acknowledgment(
        self,
    ) -> Path:
        """Generate Chappie's wake acknowledgment."""

        return self.synthesize(
            "Sir?"
        )

    def _cache_path(
        self,
        text: str,
    ) -> Path:
        """Create a stable Piper-specific cache filename."""

        cache_identity = (
            "piper-libritts-r-medium|"
            f"speaker={self.speaker_id}|"
            f"speed={self.speed}|"
            f"text={text}"
        )

        digest = hashlib.sha256(
            cache_identity.encode(
                "utf-8"
            )
        ).hexdigest()[:20]

        return (
            self.cache_dir
            / f"{digest}.wav"
        )


#
# Compatibility alias.
#
# Existing Psydekik code that still imports KokoroTTS
# continues to work while we transition the project.
#
KokoroTTS = PiperTTS


def main() -> None:
    """Speak text supplied from the command line."""

    parser = argparse.ArgumentParser(
        description=(
            "Speak through Psydekik's local TTS."
        )
    )

    parser.add_argument(
        "text",
        nargs="?",
        default="Sir?",
        help="Text for Chappie to speak.",
    )

    arguments = parser.parse_args()

    tts = PiperTTS()

    tts.warm_up()

    audio_path = tts.speak(
        arguments.text
    )

    print(
        "Voice: Piper LibriTTS-R "
        "SID 300 @ 1.00"
    )

    print(
        f"Cached audio: {audio_path}"
    )


if __name__ == "__main__":
    main()
