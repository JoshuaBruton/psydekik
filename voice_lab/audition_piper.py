from __future__ import annotations

import subprocess
import time
import wave
from pathlib import Path

import numpy as np
import sherpa_onnx


ROOT = Path(__file__).resolve().parent

MODEL_DIR = (
    ROOT
    / "models"
    / "vits-piper-en_US-libritts_r-medium"
)

OUTPUT_DIR = ROOT / "samples" / "piper"

MODEL = MODEL_DIR / "en_US-libritts_r-medium.onnx"
TOKENS = MODEL_DIR / "tokens.txt"
ESPEAK_DATA = MODEL_DIR / "espeak-ng-data"


AUDITION_TEXT = (
    "Everything looks good, sir. "
    "The Pi is online and responding normally. "
    "Nothing needs your attention right now."
)


#
# First-pass sampling across the 904-speaker space.
#
SPEAKER_IDS = [
    50,
    100,
    150,
    200,
    250,
    300,
    400,
    500,
    600,
    700,
    800,
    900,
]


def save_audio(
    audio,
    path: Path,
) -> None:
    samples = np.asarray(
        audio.samples,
        dtype=np.float32,
    )

    samples = np.clip(
        samples,
        -1.0,
        1.0,
    )

    pcm = (
        samples * 32767.0
    ).astype(np.int16)

    with wave.open(
        str(path),
        "wb",
    ) as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(
            audio.sample_rate
        )
        wav.writeframes(
            pcm.tobytes()
        )


def create_engine():
    config = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=str(MODEL),
                tokens=str(TOKENS),
                data_dir=str(ESPEAK_DATA),
            ),
            num_threads=2,
            provider="cpu",
            debug=False,
        ),
        max_num_sentences=1,
    )

    if not config.validate():
        raise RuntimeError(
            "Invalid Piper/VITS configuration."
        )

    return sherpa_onnx.OfflineTts(
        config
    )


def generate(
    tts,
    speaker_id: int,
):
    path = (
        OUTPUT_DIR
        / f"piper_sid_{speaker_id:03d}.wav"
    )

    started = time.perf_counter()

    audio = tts.generate(
        AUDITION_TEXT,
        sid=speaker_id,
        speed=1.0,
    )

    generation_time = (
        time.perf_counter()
        - started
    )

    save_audio(
        audio,
        path,
    )

    duration = (
        len(audio.samples)
        / audio.sample_rate
    )

    rtf = (
        generation_time / duration
    )

    return (
        path,
        generation_time,
        duration,
        rtf,
    )


def play(
    path: Path,
) -> None:
    subprocess.run(
        [
            "aplay",
            "--quiet",
            str(path),
        ],
        check=True,
    )


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("============================")
    print("     CHAPPIE VOICE LAB")
    print("============================")
    print()

    print("Loading Piper engine...")

    started = time.perf_counter()

    tts = create_engine()

    load_time = (
        time.perf_counter()
        - started
    )

    print(
        f"Engine ready in {load_time:.2f}s."
    )

    print()
    print(
        f'"{AUDITION_TEXT}"'
    )
    print()

    results = []

    for speaker_id in SPEAKER_IDS:
        print()
        print("-" * 55)
        print(
            f"SPEAKER {speaker_id}"
        )
        print("-" * 55)

        (
            path,
            generation_time,
            duration,
            rtf,
        ) = generate(
            tts,
            speaker_id,
        )

        print(
            f"Generation: {generation_time:.2f}s"
        )

        print(
            f"Audio:      {duration:.2f}s"
        )

        print(
            f"RTF:        {rtf:.3f}"
        )

        print(
            f"File:       {path.name}"
        )

        print()
        print(
            f"Playing speaker {speaker_id}..."
        )

        play(
            path
        )

        results.append(
            (
                speaker_id,
                generation_time,
                duration,
                rtf,
            )
        )

        while True:
            answer = input(
                "\n"
                "[Enter] next | "
                "[r] replay | "
                "[q] stop audition: "
            ).strip().lower()

            if answer == "r":
                play(
                    path
                )
                continue

            if answer == "q":
                print()
                print(
                    "Audition stopped."
                )
                break

            break

        if answer == "q":
            break

    print()
    print()
    print("============================")
    print("       RESULTS")
    print("============================")
    print()

    for (
        speaker_id,
        generation_time,
        duration,
        rtf,
    ) in results:
        print(
            f"SID {speaker_id:3d} | "
            f"gen {generation_time:5.2f}s | "
            f"audio {duration:5.2f}s | "
            f"RTF {rtf:.3f}"
        )

    print()
    print(
        f"Samples: {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()
