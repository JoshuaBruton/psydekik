import pytest

from chappie.orchestrator import ChappieOrchestrator


@pytest.fixture
def orchestrator() -> ChappieOrchestrator:
    # These deterministic routing methods do not require the full
    # model, database, voice, or MCP initialization.
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
            "where would vacation-photo.webp go?",
            ("preview", "vacation-photo.webp"),
        ),
        (
            'what category is "family vacation 2026.pdf"?',
            ("preview", "family vacation 2026.pdf"),
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
    "message",
    [
        "help me organize my week",
        "I need to organize my thoughts",
        "what category is this idea?",
        "is everything working?",
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
