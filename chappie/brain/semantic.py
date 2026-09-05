from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


MODEL_DIR = (
    Path.home()
    / ".local"
    / "share"
    / "psydekik"
    / "models"
    / "embeddings"
    / "all-MiniLM-L6-v2"
)

MODEL_PATH = MODEL_DIR / "model.onnx"
TOKENIZER_PATH = MODEL_DIR / "tokenizer.json"


INTENT_EXAMPLES = {
    "overview": [
        "How is the Pi doing?",
        "How does the system look?",
        "Is everything okay?",
        "Anything looking weird?",
        "Anything looking sketchy?",
        "Is anything wrong with the Pi?",
        "How healthy is the system?",
        "Give status update for our Pi Server",
    ],

    "cpu": [
        "What is the CPU usage?",
        "How hard is the processor working?",
        "How busy is the CPU?",
        "What's the processor load?",
        "How hard is she working right now?",
        "Is the CPU under heavy load?",
    ],

    "temperature": [
        "What is the temperature?",
        "How hot is the Pi?",
        "Is the Pi getting hot?",
        "Is she running warm?",
        "Is the processor overheating?",
        "How are the thermals?",
        "Is the Pi's temperature at a comfortable level?"
    ],

    "memory": [
        "How much RAM is being used?",
        "How much memory is available?",
        "What about RAM?",
        "Are we running low on memory?",
        "How much memory is left?",
        "What's the RAM usage?",
    ],

    "storage": [
        "How much disk space is free?",
        "How much storage do I have left?",
        "How much room have I got left?",
        "Are we running out of disk space?",
        "How much drive capacity remains?",
        "What's the free storage?",
    ],

    "uptime": [
        "How long has the Pi been running?",
        "How long has it been up?",
        "How long has she been running?",
        "What's the uptime?",
        "When was the Pi last restarted?",
        "How long since the system booted?",
    ],
}


class SemanticRouter:
    def __init__(self) -> None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found: {MODEL_PATH}"
            )

        if not TOKENIZER_PATH.exists():
            raise FileNotFoundError(
                f"Tokenizer not found: {TOKENIZER_PATH}"
            )

        print("Loading semantic router...")

        start = time.perf_counter()

        self.tokenizer = Tokenizer.from_file(
            str(TOKENIZER_PATH)
        )

        self.tokenizer.enable_truncation(
            max_length=256
        )

        self.tokenizer.enable_padding(
            pad_id=0,
            pad_token="[PAD]",
        )

        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1

        self.session = ort.InferenceSession(
            str(MODEL_PATH),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )

        self.input_names = {
            item.name
            for item in self.session.get_inputs()
        }

        self.output_names = [
            item.name
            for item in self.session.get_outputs()
        ]

        self.intent_embeddings = (
            self._build_intent_embeddings()
        )

        elapsed = time.perf_counter() - start

        print(
            f"Semantic router ready in {elapsed:.2f}s."
        )
        print(
            "Inputs:",
            sorted(self.input_names),
        )
        print(
            "Outputs:",
            self.output_names,
        )
        print()

    def _encode_batch(
        self,
        texts: list[str],
    ) -> np.ndarray:
        encodings = self.tokenizer.encode_batch(texts)

        input_ids = np.asarray(
            [e.ids for e in encodings],
            dtype=np.int64,
        )

        attention_mask = np.asarray(
            [e.attention_mask for e in encodings],
            dtype=np.int64,
        )

        feed = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }

        if "token_type_ids" in self.input_names:
            feed["token_type_ids"] = np.zeros_like(
                input_ids,
                dtype=np.int64,
            )

        outputs = self.session.run(
            None,
            feed,
        )

        # This ONNX export incorporates transformer,
        # pooling, and normalization.
        #
        # Prefer a 2-D output shaped:
        # [batch, embedding_dimension].
        for output in outputs:
            array = np.asarray(output)

            if (
                array.ndim == 2
                and array.shape[0] == len(texts)
            ):
                return self._normalize(array)

        raise RuntimeError(
            "Could not locate sentence embedding "
            f"in ONNX outputs: "
            f"{[np.asarray(x).shape for x in outputs]}"
        )

    @staticmethod
    def _normalize(
        vectors: np.ndarray,
    ) -> np.ndarray:
        vectors = vectors.astype(
            np.float32,
            copy=False,
        )

        norms = np.linalg.norm(
            vectors,
            axis=1,
            keepdims=True,
        )

        norms = np.maximum(
            norms,
            1e-12,
        )

        return vectors / norms

    def _build_intent_embeddings(
        self,
    ) -> dict[str, np.ndarray]:
        result = {}

        for intent, examples in INTENT_EXAMPLES.items():
            vectors = self._encode_batch(examples)

            centroid = vectors.mean(
                axis=0,
                keepdims=True,
            )

            centroid = self._normalize(
                centroid
            )[0]

            result[intent] = centroid

        return result

    def classify(
        self,
        text: str,
    ) -> tuple[str, float, dict[str, float]]:
        vector = self._encode_batch(
            [text]
        )[0]

        scores = {
            intent: float(
                np.dot(vector, centroid)
            )
            for intent, centroid
            in self.intent_embeddings.items()
        }

        intent = max(
            scores,
            key=scores.get,
        )

        return (
            intent,
            scores[intent],
            scores,
        )


def main() -> None:
    router = SemanticRouter()

    tests = [
        (
            "Is the Pi getting a little hot?",
            "temperature",
        ),
        (
            "How much room have I got left on this thing?",
            "storage",
        ),
        (
            "Anything looking sketchy?",
            "overview",
        ),
        (
            "How hard is she working right now?",
            "cpu",
        ),
        (
            "What about RAM?",
            "memory",
        ),
        (
            "How long has she been running?",
            "uptime",
        ),

        # Extra phrases that were NOT copied directly
        # from the original six-test benchmark.
        (
            "Do I need to worry about disk capacity?",
            "storage",
        ),
        (
            "Is this thing overheating?",
            "temperature",
        ),
        (
            "How much memory have we got available?",
            "memory",
        ),
        (
            "Does everything seem healthy?",
            "overview",
        ),
    ]

    correct = 0
    times = []

    print("=== SEMANTIC ROUTER BENCHMARK ===")
    print()

    for text, expected in tests:
        start = time.perf_counter()

        intent, confidence, scores = (
            router.classify(text)
        )

        elapsed = time.perf_counter() - start
        times.append(elapsed)

        passed = intent == expected
        correct += int(passed)

        mark = "PASS" if passed else "FAIL"

        runner_up = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )[1]

        print(
            f"{mark}  "
            f"{elapsed * 1000:7.1f} ms"
        )

        print(f"  Request:    {text}")
        print(f"  Expected:   {expected}")
        print(f"  Got:        {intent}")
        print(f"  Similarity: {confidence:.3f}")
        print(
            f"  Runner-up:  "
            f"{runner_up[0]} "
            f"({runner_up[1]:.3f})"
        )
        print()

    print(
        f"Accuracy: {correct}/{len(tests)}"
    )

    print(
        "Average classification time: "
        f"{np.mean(times) * 1000:.1f} ms"
    )


if __name__ == "__main__":
    main()
