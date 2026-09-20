from pathlib import Path

import pytest

from mcp_server.tools import file_organizer
from services.file_organizer_service import FileOrganizerService


@pytest.fixture
def isolated_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> FileOrganizerService:
    service = FileOrganizerService(
        inbox=tmp_path / "drop-box",
        assets_root=tmp_path / "assets",
    )
    monkeypatch.setattr(
        file_organizer,
        "file_organizer_service",
        service,
    )
    return service


def test_preview_file_organization(
    isolated_service: FileOrganizerService,
) -> None:
    result = file_organizer.preview_file_organization(
        "vacation-photo.webp"
    )

    assert result["status"] == "preview"
    assert result["category"] == "media/images"
    assert result["source"] == str(
        isolated_service.inbox / "vacation-photo.webp"
    )
    assert result["destination"] == str(
        isolated_service.assets_root
        / "media"
        / "images"
        / "vacation-photo.webp"
    )


@pytest.mark.parametrize(
    "filename",
    [
        "",
        ".",
        "..",
        "../private.txt",
        "folder/private.txt",
        "/etc/passwd",
    ],
)
def test_preview_rejects_unsafe_filename(
    isolated_service: FileOrganizerService,
    filename: str,
) -> None:
    result = file_organizer.preview_file_organization(filename)

    assert result["status"] == "rejected"


def test_rules_include_expected_categories() -> None:
    result = file_organizer.get_file_organization_rules()

    assert ".pdf" in result["categories"]["documents"]
    assert ".py" in result["categories"]["code"]
    assert ".webp" in result["categories"]["media/images"]
    assert ".zip" in result["categories"]["compressed"]
    assert result["unknown_category"] == "unknown"
    assert ".part" in result["temporary_suffixes_ignored"]
