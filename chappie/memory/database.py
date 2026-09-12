"""Persistent SQLite conversation journal for Chappie."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "chappie.db"
)


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class ChappieMemoryDB:
    """Persist conversations and messages locally in SQLite."""

    def __init__(
        self,
        path: Path = DEFAULT_DB_PATH,
    ) -> None:
        self.path = path
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.connection = sqlite3.connect(
            self.path
        )

        self.connection.row_factory = (
            sqlite3.Row
        )

        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                display_text TEXT,
                speech_text TEXT,
                route TEXT,
                created_at TEXT NOT NULL,
                metadata_json TEXT,
                FOREIGN KEY (
                    conversation_id
                )
                REFERENCES conversations(id)
            );

            CREATE INDEX IF NOT EXISTS
            idx_messages_conversation
            ON messages(
                conversation_id,
                id
            );

            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'explicit',
                importance REAL NOT NULL DEFAULT 1.0,
                confidence REAL NOT NULL DEFAULT 1.0,
                source_conversation_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_used_at TEXT,
                FOREIGN KEY (
                    source_conversation_id
                )
                REFERENCES conversations(id)
            );

            CREATE INDEX IF NOT EXISTS
            idx_memories_kind
            ON memories(kind);

            CREATE INDEX IF NOT EXISTS
            idx_memories_updated
            ON memories(updated_at);
            """
        )

        self.connection.commit()

    def start_conversation(self) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO conversations (
                started_at
            )
            VALUES (?)
            """,
            (
                utc_now(),
            ),
        )

        self.connection.commit()

        return int(cursor.lastrowid)

    def end_conversation(
        self,
        conversation_id: int,
    ) -> None:
        self.connection.execute(
            """
            UPDATE conversations
            SET ended_at = ?
            WHERE id = ?
            """,
            (
                utc_now(),
                conversation_id,
            ),
        )

        self.connection.commit()

    def add_user_message(
        self,
        *,
        conversation_id: int,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        return self._add_message(
            conversation_id=conversation_id,
            role="user",
            text=text,
            metadata=metadata,
        )

    def add_assistant_message(
        self,
        *,
        conversation_id: int,
        display_text: str,
        speech_text: str,
        route: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        return self._add_message(
            conversation_id=conversation_id,
            role="assistant",
            text=speech_text,
            display_text=display_text,
            speech_text=speech_text,
            route=route,
            metadata=metadata,
        )

    def _add_message(
        self,
        *,
        conversation_id: int,
        role: str,
        text: str,
        display_text: str | None = None,
        speech_text: str | None = None,
        route: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO messages (
                conversation_id,
                role,
                text,
                display_text,
                speech_text,
                route,
                created_at,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                role,
                text,
                display_text,
                speech_text,
                route,
                utc_now(),
                (
                    json.dumps(metadata)
                    if metadata is not None
                    else None
                ),
            ),
        )

        self.connection.commit()

        return int(cursor.lastrowid)

    def remember(
        self,
        *,
        content: str,
        conversation_id: int | None = None,
        kind: str = "explicit",
        importance: float = 1.0,
        confidence: float = 1.0,
    ) -> int:
        """Store a durable memory."""

        content = content.strip()

        if not content:
            raise ValueError(
                "Memory content cannot be empty."
            )

        now = utc_now()

        cursor = self.connection.execute(
            """
            INSERT INTO memories (
                content,
                kind,
                importance,
                confidence,
                source_conversation_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                content,
                kind,
                importance,
                confidence,
                conversation_id,
                now,
                now,
            ),
        )

        self.connection.commit()

        return int(cursor.lastrowid)

    def find_memories(
        self,
        query: str,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Find durable memories containing the supplied text."""

        query = query.strip().casefold()

        if not query:
            return []

        rows = self.connection.execute(
            """
            SELECT
                id,
                content,
                kind,
                importance,
                confidence,
                source_conversation_id,
                created_at,
                updated_at,
                last_used_at
            FROM memories
            WHERE LOWER(content) LIKE ?
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (
                f"%{query}%",
                limit,
            ),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def forget_memories(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        """Delete durable memories matching supplied text."""

        matches = self.find_memories(
            query,
            limit=100,
        )

        if not matches:
            return []

        ids = [
            int(memory["id"])
            for memory in matches
        ]

        placeholders = ",".join(
            "?"
            for _ in ids
        )

        self.connection.execute(
            f"""
            DELETE FROM memories
            WHERE id IN ({placeholders})
            """,
            ids,
        )

        self.connection.commit()

        return matches

    def recent_memories(
        self,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return durable memories, newest first."""

        rows = self.connection.execute(
            """
            SELECT
                id,
                content,
                kind,
                importance,
                confidence,
                source_conversation_id,
                created_at,
                updated_at,
                last_used_at
            FROM memories
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (
                limit,
            ),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def mark_memory_used(
        self,
        memory_id: int,
    ) -> None:
        """Record that a durable memory was retrieved."""

        self.connection.execute(
            """
            UPDATE memories
            SET last_used_at = ?
            WHERE id = ?
            """,
            (
                utc_now(),
                memory_id,
            ),
        )

        self.connection.commit()

    def recent_messages(
        self,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
                id,
                conversation_id,
                role,
                text,
                display_text,
                speech_text,
                route,
                created_at,
                metadata_json
            FROM messages
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                limit,
            ),
        ).fetchall()

        return [
            dict(row)
            for row in reversed(rows)
        ]

    def close(self) -> None:
        self.connection.close()
