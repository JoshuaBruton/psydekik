from pathlib import Path

import pytest

from services.file_organizer_service import FileOrganizerService


@pytest.fixture
def organizer(tmp_path: Path) -> FileOrganizerService:
    return FileOrganizerService(
        inbox=tmp_path / "drop-box",
        assets_root=tmp_path / "assets",
    )


@pytest.mark.parametrize(
    ("filename", "expected_category"),
    [
        ("report.pdf", "documents"),
        ("script.PY", "code"),
        ("photo.webp", "media/images"),
        ("animation.gif", "media/gif"),
        ("movie.mp4", "media/video"),
        ("song.flac", "media/audio"),
        ("backup.zip", "compressed"),
        ("mystery.xyz", "unknown"),
    ],
)
def test_classify_files(
    organizer: FileOrganizerService,
    filename: str,
    expected_category: str,
) -> None:
    assert organizer.classify(filename) == expected_category


def test_preview_does_not_move_file(
    organizer: FileOrganizerService,
) -> None:
    source = organizer.inbox / "family-notes.pdf"
    source.write_text("Important notes", encoding="utf-8")

    result = organizer.preview(source)

    assert result.status == "preview"
    assert result.category == "documents"
    assert result.destination == str(
        organizer.assets_root
        / "documents"
        / "family-notes.pdf"
    )
    assert source.exists()


def test_organize_moves_file(
    organizer: FileOrganizerService,
) -> None:
    source = organizer.inbox / "photo.webp"
    source.write_bytes(b"image-data")

    result = organizer.organize(source)
    destination = (
        organizer.assets_root
        / "media"
        / "images"
        / "photo.webp"
    )

    assert result.status == "organized"
    assert result.category == "media/images"
    assert result.destination == str(destination)
    assert not source.exists()
    assert destination.read_bytes() == b"image-data"


def test_duplicate_filename_is_preserved(
    organizer: FileOrganizerService,
) -> None:
    destination_directory = (
        organizer.assets_root
        / "documents"
    )
    existing = destination_directory / "report.pdf"
    existing.write_bytes(b"original")

    source = organizer.inbox / "report.pdf"
    source.write_bytes(b"new")

    result = organizer.organize(source)
    duplicate = destination_directory / "report_1.pdf"

    assert result.status == "organized"
    assert result.destination == str(duplicate)
    assert existing.read_bytes() == b"original"
    assert duplicate.read_bytes() == b"new"


def test_unknown_extension_moves_to_unknown(
    organizer: FileOrganizerService,
) -> None:
    source = organizer.inbox / "mystery.xyz"
    source.write_text("unknown data", encoding="utf-8")

    result = organizer.organize(source)
    destination = (
        organizer.assets_root
        / "unknown"
        / "mystery.xyz"
    )

    assert result.status == "organized"
    assert result.category == "unknown"
    assert destination.exists()


def test_temporary_file_is_ignored(
    organizer: FileOrganizerService,
) -> None:
    source = organizer.inbox / "download.part"
    source.write_bytes(b"incomplete")

    result = organizer.organize(source)

    assert result.status == "ignored"
    assert result.destination is None
    assert source.exists()


def test_file_outside_inbox_is_rejected(
    organizer: FileOrganizerService,
    tmp_path: Path,
) -> None:
    outside_file = tmp_path / "outside.pdf"
    outside_file.write_bytes(b"outside")

    with pytest.raises(
        ValueError,
        match="outside organizer inbox",
    ):
        organizer.preview(outside_file)


def test_status_lists_pending_files(
    organizer: FileOrganizerService,
) -> None:
    (organizer.inbox / "second.txt").write_text(
        "second",
        encoding="utf-8",
    )
    (organizer.inbox / "first.pdf").write_bytes(b"first")
    (organizer.inbox / "ignored.tmp").write_bytes(b"partial")

    status = organizer.status()

    assert status["pending_count"] == 2
    assert status["pending_files"] == [
        "first.pdf",
        "second.txt",
    ]
    assert status["known_extensions"] == 69


def test_default_inbox_uses_incoming_directory() -> None:
    from services.file_organizer_service import (
        DEFAULT_INBOX,
        PROJECT_ROOT,
    )

    assert DEFAULT_INBOX == (
        PROJECT_ROOT / "drop-box" / "incoming"
    )
