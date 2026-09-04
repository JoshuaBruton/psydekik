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

OUTPUT_DIR = (
    ROOT
    / "samples"
    / "finalists"
)

MODEL = MODEL_DIR / "en_US-libritts_r-medium.onnx"
TOKENS = MODEL_DIR / "tokens.txt"
ESPEAK_DATA = MODEL_DIR / "espeak-ng-data"


#
# SID 300 is our current champion.
#
# The others give us another concentrated sample
# around that part of the speaker collection.
#
SPEAKER_IDS = [
    260,
    270,
    280,
    290,
    295,
    300,
    305,
    310,
    320,
    330,
    340,
]


TEST_LINES = [
    (
        "status",
        "Everything looks good, sir."
    ),
    (
        "greeting",
        "Good morning, sir. What can I do for you?"
    ),
    (
        "warning",
        "The Pi is running a little warm. "
        "Nothing critical, but I'll keep an eye on it."
    ),
    (
        "storage",
        "You've got about thirty-one gigs "
        "of storage left."
    ),
    (
        "problem",
        "I found the problem. "
        "The external drive isn't responding."
    ),
    (
        "retry",
        "Sorry, sir. I didn't quite catch that."
    ),
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


def generate_line(
    tts,
    speaker_id: int,
    label: str,
    text: str,
):
    output = (
        OUTPUT_DIR
        / f"sid_{speaker_id:03d}_{label}.wav"
    )

    started = time.perf_counter()

    audio = tts.generate(
        text,
        sid=speaker_id,
        speed=1.0,
    )

    generation_time = (
        time.perf_counter()
        - started
    )

    duration = (
        len(audio.samples)
        / audio.sample_rate
    )

    rtf = (
        generation_time / duration
        if duration
        else 0.0
    )

    save_audio(
        audio,
        output,
    )

    return (
        output,
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
    print("================================")
    print("     CHAPPIE VOICE FINALS")
    print("================================")
    print()

    print("Loading Piper engine...")

    started = time.perf_counter()

    tts = create_engine()

    print(
        f"Ready in "
        f"{time.perf_counter() - started:.2f}s."
    )

    results = []

    for speaker_id in SPEAKER_IDS:
        print()
        print("=" * 64)

        if speaker_id == 300:
            print(
                "SID 300  ★ CURRENT CHAMPION ★"
            )
        else:
            print(
                f"SID {speaker_id}"
            )

        print("=" * 64)

        speaker_results = []

        for (
            label,
            text,
        ) in TEST_LINES:
            print()
            print(
                f"[{label}] {text}"
            )

            (
                output,
                generation_time,
                duration,
                rtf,
            ) = generate_line(
                tts,
                speaker_id,
                label,
                text,
            )

            print(
                f"  gen {generation_time:.2f}s | "
                f"audio {duration:.2f}s | "
                f"RTF {rtf:.3f}"
            )

            play(
                output
            )

            speaker_results.append(
                (
                    label,
                    generation_time,
                    duration,
                    rtf,
                )
            )

        results.append(
            (
                speaker_id,
                speaker_results,
            )
        )

        print()

        while True:
            answer = input(
                "[Enter] next speaker | "
                "[r] replay speaker | "
                "[q] finish: "
            ).strip().lower()

            if answer == "r":
                print()

                for (
                    label,
                    _,
                ) in TEST_LINES:
                    output = (
                        OUTPUT_DIR
                        / (
                            f"sid_{speaker_id:03d}_"
                            f"{label}.wav"
                        )
                    )

                    play(
                        output
                    )

                continue

            break

        if answer == "q":
            break

    print()
    print()
    print("================================")
    print("        PERFORMANCE")
    print("================================")
    print()

    for (
        speaker_id,
        speaker_results,
    ) in results:
        generation_total = sum(
            result[1]
            for result in speaker_results
        )

        duration_total = sum(
            result[2]
            for result in speaker_results
        )

        overall_rtf = (
            generation_total / duration_total
            if duration_total
            else 0.0
        )

        marker = (
            " ★"
            if speaker_id == 300
            else ""
        )

        print(
            f"SID {speaker_id:3d}{marker} | "
            f"gen {generation_total:5.2f}s | "
            f"audio {duration_total:5.2f}s | "
            f"RTF {overall_rtf:.3f}"
        )

    print()
    print(
        f"Samples saved to:\n{OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()
