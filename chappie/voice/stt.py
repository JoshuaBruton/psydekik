import argparse
import os
import wave
from pathlib import Path

import numpy as np
import sherpa_onnx


DEFAULT_MODEL_DIR = (
    Path.home()
    / ".local/share/psydekik/models/stt/"
    "sherpa-onnx-zipformer-small-en-2023-06-26"
)


class SpeechToText:
    """Transcribe recorded speech locally with Sherpa-ONNX."""

    def __init__(
        self,
        model_dir: Path | None = None,
        num_threads: int = 2,
    ) -> None:
        configured_model_dir = os.getenv(
            "PSYDEKIK_STT_MODEL_DIR"
        )

        self.model_dir = (
            model_dir
            or (
                Path(configured_model_dir).expanduser()
                if configured_model_dir
                else DEFAULT_MODEL_DIR
            )
        )

        self.num_threads = num_threads

        self.encoder = (
            self.model_dir
            / "encoder-epoch-99-avg-1.int8.onnx"
        )
        self.decoder = (
            self.model_dir
            / "decoder-epoch-99-avg-1.onnx"
        )
        self.joiner = (
            self.model_dir
            / "joiner-epoch-99-avg-1.int8.onnx"
        )
        self.tokens = self.model_dir / "tokens.txt"

        self._validate_model_files()
        self.recognizer = self._create_recognizer()

    def _validate_model_files(self) -> None:
        required_paths = (
            self.encoder,
            self.decoder,
            self.joiner,
            self.tokens,
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
                f"Missing STT model files: {missing}"
            )

    def _create_recognizer(
        self,
    ) -> sherpa_onnx.OfflineRecognizer:
        return sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(self.encoder),
            decoder=str(self.decoder),
            joiner=str(self.joiner),
            tokens=str(self.tokens),
            num_threads=self.num_threads,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search",
            debug=False,
            provider="cpu",
        )

    def transcribe(
        self,
        audio_path: str | Path,
    ) -> str:
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(
                f"Audio file does not exist: {audio_path}"
            )

        sample_rate, samples = self._read_wav(
            audio_path
        )

        stream = self.recognizer.create_stream()

        stream.accept_waveform(
            sample_rate,
            samples,
        )

        self.recognizer.decode_stream(stream)

        return stream.result.text.strip()

    @staticmethod
    def _read_wav(
        audio_path: Path,
    ) -> tuple[int, np.ndarray]:
        with wave.open(
            str(audio_path),
            "rb",
        ) as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()

            frames = wav_file.readframes(
                wav_file.getnframes()
            )

        if channels != 1:
            raise ValueError(
                "STT expects a mono WAV file."
            )

        if sample_width != 2:
            raise ValueError(
                "STT expects 16-bit PCM audio."
            )

        samples = np.frombuffer(
            frames,
            dtype=np.int16,
        ).astype(np.float32)

        samples /= 32768.0

        return sample_rate, samples


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Transcribe a WAV file with "
            "Psydekik local STT."
        )
    )

    parser.add_argument(
        "audio_path",
        nargs="?",
        default="/tmp/psydekik-command.wav",
        help=(
            "Path to a mono 16-bit PCM WAV file."
        ),
    )

    args = parser.parse_args()

    stt = SpeechToText()
    text = stt.transcribe(
        args.audio_path
    )

    print(f'You said: "{text}"')


if __name__ == "__main__":
    main()
