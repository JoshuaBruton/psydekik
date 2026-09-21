import pytest

from chappie.orchestrator import ChappieOrchestrator


@pytest.fixture
def orchestrator() -> ChappieOrchestrator:
    # Deterministic routing does not require full model,
    # database, voice, or MCP initialization.
    return object.__new__(ChappieOrchestrator)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "is the file organizer running?",
            ("status", None),
        ),
        (
            "what file types can you organize?",
            ("rules", None),
        ),
        (
            "what types of files can you organize?",
            ("rules", None),
        ),
        (
            "which formats does the organizer support?",
            ("rules", None),
        ),
        (
            "what file formats do you recognize?",
            ("rules", None),
        ),
        (
            "where would vacation-photo.webp go?",
            ("preview", "vacation-photo.webp"),
        ),
        (
            'what category is "family vacation 2026.pdf"?',
            ("preview", "family vacation 2026.pdf"),
        ),
        (
            "where would vacation photo dot web p go?",
            ("preview", "vacation-photo.webp"),
        ),
        (
            "where would school notes dot p d f go?",
            ("preview", "school-notes.pdf"),
        ),
        (
            "where do web p images go?",
            ("preview", "example.webp"),
        ),
        (
            "what folder does a p d f file go into?",
            ("preview", "example.pdf"),
        ),
        (
            "tell me about the file organizer",
            ("clarify", None),
        ),
        (
            "what folder should this image use?",
            ("clarify", None),
        ),
    ],
)
def test_detect_file_organizer_request(
    orchestrator: ChappieOrchestrator,
    message: str,
    expected: tuple[str, str | None],
) -> None:
    assert (
        orchestrator._detect_file_organizer_request(message)
        == expected
    )


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "vacation photo dot web p",
            "vacation photo.webp",
        ),
        (
            "report dot p d f",
            "report.pdf",
        ),
        (
            "picture dot p n g",
            "picture.png",
        ),
        (
            "clip dot m p four",
            "clip.mp4",
        ),
        (
            "song dot m p three",
            "song.mp3",
        ),
    ],
)
def test_normalize_spoken_file_terms(
    orchestrator: ChappieOrchestrator,
    message: str,
    expected: str,
) -> None:
    assert (
        orchestrator._normalize_spoken_file_terms(message)
        == expected
    )


@pytest.mark.parametrize(
    "message",
    [
        "help me organize my week",
        "I need to organize my thoughts",
        "what category is this idea?",
        "is everything working?",
        "where would you like to go on vacation?",
        "what category of music is reggae?",
        "what types of music do you recognize?",
    ],
)
def test_unrelated_requests_are_not_captured(
    orchestrator: ChappieOrchestrator,
    message: str,
) -> None:
    assert (
        orchestrator._detect_file_organizer_request(message)
        is None
    )
