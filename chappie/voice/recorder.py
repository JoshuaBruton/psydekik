import argparse
import os
import wave
from collections import deque
from pathlib import Path
from time import monotonic

import numpy as np
import sounddevice as sd


SAMPLE_RATE = 16_000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
BLOCK_DURATION_MS = 30
BLOCK_SIZE = SAMPLE_RATE * BLOCK_DURATION_MS // 1000

DEFAULT_OUTPUT_PATH = Path(
    "/tmp/psydekik-command.wav"
)


class VoiceRecorder:
    """Record a spoken command and stop after silence."""

    def __init__(
        self,
        device: int | None = None,
        sample_rate: int = SAMPLE_RATE,
        calibration_seconds: float = 1.0,
    speech_timeout_seconds: float = 8.0,
    silence_seconds: float = 1.5,
    maximum_seconds: float = 20.0,
    pre_roll_seconds: float = 0.5,
    threshold_multiplier: float = 1.8,
    minimum_threshold: float = 250.0,
    ) -> None:
        self.device = (
            device
            if device is not None
            else self._find_input_device()
        )

        self.sample_rate = sample_rate
        self.calibration_seconds = calibration_seconds
        self.speech_timeout_seconds = speech_timeout_seconds
        self.silence_seconds = silence_seconds
        self.maximum_seconds = maximum_seconds
        self.pre_roll_seconds = pre_roll_seconds
        self.threshold_multiplier = threshold_multiplier
        self.minimum_threshold = minimum_threshold

        self.block_size = (
            self.sample_rate
            * BLOCK_DURATION_MS
            // 1000
        )

    def record(
        self,
        output_path: Path = DEFAULT_OUTPUT_PATH,
    ) -> Path:
        """Record one command and save it as a WAV file."""

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        calibration_blocks = max(
            1,
            int(
                self.calibration_seconds
                * self.sample_rate
                / self.block_size
            ),
        )

        silence_blocks_required = max(
            1,
            int(
                self.silence_seconds
                * self.sample_rate
                / self.block_size
            ),
        )

        pre_roll_blocks = max(
            1,
            int(
                self.pre_roll_seconds
                * self.sample_rate
                / self.block_size
            ),
        )

        frames: list[bytes] = []
        pre_roll: deque[bytes] = deque(
            maxlen=pre_roll_blocks
        )

        noise_levels: list[float] = []
        speech_started = False
        silent_blocks = 0
        recording_started_at = monotonic()

        print(
            f"Using input device {self.device}: "
            f"{sd.query_devices(self.device)['name']}"
        )
        print("Calibrating background noise...")

        with sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            device=self.device,
            channels=CHANNELS,
            dtype="int16",
        ) as stream:
            for _ in range(calibration_blocks):
                block, overflowed = stream.read(
                    self.block_size
                )

                if overflowed:
                    print(
                        "Warning: microphone input overflowed "
                        "during calibration."
                    )

                noise_levels.append(
                    self._rms(bytes(block))
                )

            average_noise = (
                sum(noise_levels) / len(noise_levels)
            )

            threshold = max(
	        self.minimum_threshold,
       		average_noise * self.threshold_multiplier,
        	average_noise + 500.0,
            )


            print(
                f"Noise level: {average_noise:.1f}"
            )
            print(
                f"Speech threshold: {threshold:.1f}"
            )
            print("Listening—speak now.")

            waiting_started_at = monotonic()

            while True:
                block, overflowed = stream.read(
                    self.block_size
                )
                block_bytes = bytes(block)

                if overflowed:
                    print(
                        "Warning: microphone input overflowed."
                    )

                level = self._rms(block_bytes)
                is_speech = level >= threshold

                if not speech_started:
                    pre_roll.append(block_bytes)

                    if is_speech:
                        speech_started = True
                        frames.extend(pre_roll)
                        pre_roll.clear()

                        recording_started_at = monotonic()
                        print("Speech detected.")

                    elif (
                        monotonic() - waiting_started_at
                        >= self.speech_timeout_seconds
                    ):
                        raise TimeoutError(
                            "No speech was detected."
                        )

                    continue

                frames.append(block_bytes)

                if is_speech:
                    silent_blocks = 0
                else:
                    silent_blocks += 1

                if silent_blocks >= silence_blocks_required:
                    print("Silence detected.")
                    break

                if (
                    monotonic() - recording_started_at
                    >= self.maximum_seconds
                ):
                    print(
                        "Maximum recording duration reached."
                    )
                    break

        self._write_wav(
            output_path=output_path,
            frames=frames,
        )

        duration = (
            len(frames)
            * self.block_size
            / self.sample_rate
        )

        print(
            f"Saved {duration:.2f} seconds to "
            f"{output_path}"
        )

        return output_path

    @staticmethod
    def _rms(audio_bytes: bytes) -> float:
        """Calculate the RMS volume of signed 16-bit audio."""

        samples = np.frombuffer(
            audio_bytes,
            dtype=np.int16,
        ).astype(np.float32)

        if samples.size == 0:
            return 0.0

        return float(
            np.sqrt(np.mean(np.square(samples)))
        )

    def _write_wav(
        self,
        output_path: Path,
        frames: list[bytes],
    ) -> None:
        """Write captured PCM frames to a WAV file."""

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(b"".join(frames))

    @staticmethod
    def _find_input_device() -> int:
        """Find the configured or TONOR input device."""

        configured_device = os.getenv(
            "PSYDEKIK_AUDIO_INPUT"
        )

        if configured_device is not None:
            return int(configured_device)

        for index, device in enumerate(
            sd.query_devices()
        ):
            device_name = str(device["name"]).casefold()

            if (
                device["max_input_channels"] > 0
                and "tonor" in device_name
            ):
                return index

        default_input = sd.default.device[0]

        if default_input is None or default_input < 0:
            raise RuntimeError(
                "No microphone input device was found."
            )

        return int(default_input)


def main() -> None:
    """Record one spoken command from the terminal."""

    parser = argparse.ArgumentParser(
        description=(
            "Record a spoken Psydekik command."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Destination WAV file.",
    )

    arguments = parser.parse_args()

    recorder = VoiceRecorder()
    recorder.record(arguments.output)


if __name__ == "__main__":
    main()
