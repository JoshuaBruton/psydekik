"""Streaming wake-word detection for Chappie."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import sherpa_onnx
import sounddevice as sd


class ChappieWakeWord:
    """Detect the phrase 'Hey Chappie' from the microphone."""

    SAMPLE_RATE = 16000
    BLOCK_SECONDS = 0.10

    def __init__(
        self,
        device: int | str | None = None,
    ) -> None:
        self.device = device

        model_dir = (
            Path.home()
            / ".local"
            / "share"
            / "psydekik"
            / "models"
            / "kws"
            / "sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01"
        )

        keywords_file = (
            Path(__file__).parent
            / "wake"
            / "keywords.txt"
        )

        required_files = (
            model_dir
            / "encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx",
            model_dir
            / "decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx",
            model_dir
            / "joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx",
            model_dir / "tokens.txt",
            keywords_file,
        )

        for path in required_files:
            if not path.is_file():
                raise FileNotFoundError(
                    f"Missing wake-word file: {path}"
                )

        self.model_dir = model_dir
        self.keywords_file = keywords_file

        print("Loading wake-word engine...")

        self.spotter = self._create_spotter()

        self.samples_per_block = int(
            self.SAMPLE_RATE
            * self.BLOCK_SECONDS
        )

        print(
            'Wake word ready: "Hey Chappie"'
        )

    def _create_spotter(
        self,
    ) -> sherpa_onnx.KeywordSpotter:
        """Create a fresh keyword spotter instance."""

        return sherpa_onnx.KeywordSpotter(
            tokens=str(
                self.model_dir / "tokens.txt"
            ),
            encoder=str(
                self.model_dir
                / "encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
            ),
            decoder=str(
                self.model_dir
                / "decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
            ),
            joiner=str(
                self.model_dir
                / "joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
            ),
            keywords_file=str(
                self.keywords_file
            ),
            num_threads=1,
            provider="cpu",
            max_active_paths=4,
            keywords_score=1.5,
            keywords_threshold=0.25,
            num_trailing_blanks=1,
        )

    def wait(self) -> str:
        """Block until the configured wake phrase is detected."""

        #
        # Rebuild the native KWS engine for every wake cycle.
        # This avoids stale internal state after repeated hits.
        #
        self.spotter = self._create_spotter()

        stream = self.spotter.create_stream()

        print()
        print(
            'Sleeping. Say "Hey Chappie"...'
        )

        with sd.InputStream(
            device=self.device,
            channels=1,
            dtype="float32",
            samplerate=self.SAMPLE_RATE,
            blocksize=self.samples_per_block,
        ) as audio_stream:

            block_count = 0

            while True:
                samples, overflowed = (
                    audio_stream.read(
                        self.samples_per_block
                    )
                )

                if overflowed:
                    continue

                samples = np.asarray(
                    samples,
                    dtype=np.float32,
                ).reshape(-1)

                block_count += 1

                #
                # Temporary reliability diagnostic.
                # Print roughly once every 5 seconds.
                #
                if block_count % 50 == 0:
                    rms = float(
                        np.sqrt(
                            np.mean(
                                np.square(samples)
                            )
                        )
                    )

                    print(
                        "Wake audio heartbeat: "
                        f"RMS={rms:.5f}"
                    )

                stream.accept_waveform(
                    self.SAMPLE_RATE,
                    samples,
                )

                while self.spotter.is_ready(
                    stream
                ):
                    self.spotter.decode_stream(
                        stream
                    )

                result = (
                    self.spotter.get_result(
                        stream
                    )
                )

                if result:
                    phrase = str(result).strip()

                    self.spotter.reset_stream(
                        stream
                    )

                    print(
                        "Wake word detected: "
                        f"{phrase}"
                    )

                    return phrase


if __name__ == "__main__":
    ChappieWakeWord().wait()
