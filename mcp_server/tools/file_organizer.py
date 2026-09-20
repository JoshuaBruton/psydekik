"""MCP tools for inspecting Psydekik's file organizer."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Final

from mcp.server import MCPServer

from services.file_organizer_service import (
    CATEGORY_EXTENSIONS,
    FileOrganizerService,
)


SERVICE_UNIT: Final[str] = "psydekik-file-organizer.service"

file_organizer_service = FileOrganizerService()


def _systemctl_state(command: str) -> str:
    """Return a safe textual state for the organizer's systemd unit."""

    try:
        completed = subprocess.run(
            ["systemctl", command, SERVICE_UNIT],
            capture_output=True,
            check=False,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"unavailable: {exc}"

    output = completed.stdout.strip() or completed.stderr.strip()
    return output or "unknown"


def get_file_organizer_status() -> dict[str, Any]:
    """Return organizer service state and files currently awaiting processing."""

    status = file_organizer_service.status()

    return {
        **status,
        "service_unit": SERVICE_UNIT,
        "service_active": _systemctl_state("is-active"),
        "service_enabled": _systemctl_state("is-enabled"),
    }


def preview_file_organization(filename: str) -> dict[str, Any]:
    """Preview where a filename would be placed without moving any file."""

    candidate = Path(filename)

    if (
        not filename.strip()
        or candidate.is_absolute()
        or candidate.name != filename
        or filename in {".", ".."}
    ):
        return {
            "status": "rejected",
            "filename": filename,
            "message": (
                "Provide one filename only, without a directory path."
            ),
        }

    source = file_organizer_service.inbox / filename

    try:
        return file_organizer_service.preview(source).to_dict()
    except ValueError as exc:
        return {
            "status": "rejected",
            "filename": filename,
            "message": str(exc),
        }


def get_file_organization_rules() -> dict[str, Any]:
    """Return the file categories and extensions recognized by Psydekik."""

    return {
        "categories": {
            category: sorted(extensions)
            for category, extensions in CATEGORY_EXTENSIONS.items()
        },
        "unknown_category": "unknown",
        "temporary_suffixes_ignored": [
            ".crdownload",
            ".download",
            ".part",
            ".partial",
            ".tmp",
        ],
    }


def register_file_organizer_tools(server: MCPServer) -> None:
    """Register read-only file-organizer tools with Psydekik MCP."""

    server.tool()(get_file_organizer_status)
    server.tool()(preview_file_organization)
    server.tool()(get_file_organization_rules)
