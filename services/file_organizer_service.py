"""Deterministic and reusable file-organization logic for Psydekik."""

from __future__ import annotations

import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final


PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
DEFAULT_INBOX: Final[Path] = (
    PROJECT_ROOT / "drop-box" / "incoming"
)
DEFAULT_ASSETS_ROOT: Final[Path] = PROJECT_ROOT / "chappie" / "assets"

IGNORED_SUFFIXES: Final[set[str]] = {
    ".crdownload",
    ".download",
    ".part",
    ".partial",
    ".tmp",
}

CATEGORY_EXTENSIONS: Final[dict[str, set[str]]] = {
    "documents": {
        ".txt", ".pdf", ".doc", ".docx",
        ".xls", ".xlsx", ".ppt", ".pptx",
        ".odt", ".ods", ".odp", ".pages",
        ".csv",
    },
    "code": {
        ".py", ".js", ".ts", ".html", ".css",
        ".java", ".cpp", ".c", ".cs", ".php",
        ".rb", ".go", ".swift", ".lua",
        ".sh", ".bash", ".bat", ".ps1",
        ".sql", ".json", ".xml", ".yaml",
        ".yml", ".toml", ".md",
    },
    "media/images": {
        ".png", ".jpg", ".jpeg", ".webp",
        ".bmp", ".tif", ".tiff", ".svg",
    },
    "media/gif": {
        ".gif",
    },
    "media/video": {
        ".mp4", ".avi", ".mov", ".mkv",
        ".mpg", ".mpeg", ".webm", ".m4v",
    },
    "media/audio": {
        ".mp3", ".wav", ".flac", ".m4a",
        ".aac", ".ogg", ".opus",
    },
    "compressed": {
        ".zip", ".7z", ".rar", ".tar",
        ".gz", ".bz2", ".xz",
    },
}


@dataclass(frozen=True, slots=True)
class OrganizationResult:
    status: str
    source: str
    destination: str | None
    category: str | None
    message: str

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


class FileOrganizerService:
    """Classify and move files from a controlled inbox into Psydekik assets."""

    def __init__(
        self,
        inbox: Path = DEFAULT_INBOX,
        assets_root: Path = DEFAULT_ASSETS_ROOT,
    ) -> None:
        self.inbox = inbox.expanduser().resolve()
        self.assets_root = assets_root.expanduser().resolve()
        self.extension_categories = self._build_extension_index()
        self.ensure_directories()

    @staticmethod
    def _build_extension_index() -> dict[str, str]:
        index: dict[str, str] = {}

        for category, extensions in CATEGORY_EXTENSIONS.items():
            for extension in extensions:
                normalized = extension.lower()

                if normalized in index:
                    raise ValueError(
                        f"Duplicate extension mapping: {normalized}"
                    )

                index[normalized] = category

        return index

    def ensure_directories(self) -> None:
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.assets_root.mkdir(parents=True, exist_ok=True)

        for category in CATEGORY_EXTENSIONS:
            (self.assets_root / category).mkdir(
                parents=True,
                exist_ok=True,
            )

        (self.assets_root / "unknown").mkdir(
            parents=True,
            exist_ok=True,
        )

    def classify(self, file_path: str | Path) -> str:
        path = Path(file_path)
        return self.extension_categories.get(
            path.suffix.lower(),
            "unknown",
        )

    def destination_directory(self, file_path: str | Path) -> Path:
        return self.assets_root / self.classify(file_path)

    def is_ignored(self, file_path: str | Path) -> bool:
        path = Path(file_path)

        return (
            path.name.startswith(".")
            or path.name.endswith("~")
            or path.suffix.lower() in IGNORED_SUFFIXES
        )

    def _validate_source(self, file_path: str | Path) -> Path:
        source = Path(file_path).expanduser().resolve()

        if source.parent != self.inbox:
            raise ValueError(
                f"Refusing file outside organizer inbox: {source}"
            )

        return source

    @staticmethod
    def _available_destination(destination: Path) -> Path:
        if not destination.exists():
            return destination

        counter = 1

        while True:
            candidate = (
                destination.parent
                / f"{destination.stem}_{counter}{destination.suffix}"
            )

            if not candidate.exists():
                return candidate

            counter += 1

    def preview(self, file_path: str | Path) -> OrganizationResult:
        source = self._validate_source(file_path)

        if self.is_ignored(source):
            return OrganizationResult(
                status="ignored",
                source=str(source),
                destination=None,
                category=None,
                message="Temporary or hidden file will be ignored.",
            )

        category = self.classify(source)
        destination = self._available_destination(
            self.assets_root / category / source.name
        )

        return OrganizationResult(
            status="preview",
            source=str(source),
            destination=str(destination),
            category=category,
            message=f"File will be organized as {category}.",
        )

    def organize(self, file_path: str | Path) -> OrganizationResult:
        preview = self.preview(file_path)
        source = Path(preview.source)

        if preview.status == "ignored":
            return preview

        if not source.exists():
            return OrganizationResult(
                status="missing",
                source=str(source),
                destination=None,
                category=preview.category,
                message="Source file no longer exists.",
            )

        if not source.is_file():
            return OrganizationResult(
                status="ignored",
                source=str(source),
                destination=None,
                category=None,
                message="Source is not a regular file.",
            )

        destination = Path(preview.destination or "")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))

        return OrganizationResult(
            status="organized",
            source=str(source),
            destination=str(destination),
            category=preview.category,
            message=f"Moved {source.name} into {preview.category}.",
        )

    def pending_files(self) -> list[Path]:
        return sorted(
            path
            for path in self.inbox.iterdir()
            if path.is_file() and not self.is_ignored(path)
        )

    def status(self) -> dict[str, object]:
        pending = self.pending_files()

        return {
            "inbox": str(self.inbox),
            "assets_root": str(self.assets_root),
            "pending_count": len(pending),
            "pending_files": [path.name for path in pending],
            "known_extensions": len(self.extension_categories),
        }
