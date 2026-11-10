import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

class AutomationStore:
    """Persistent automation definitions. Scheduling/dispatch is intentionally separate."""

    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS automations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    interval_minutes INTEGER NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def create(self, name: str, prompt: str, interval_minutes: int) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        item_id = str(uuid4())
        with self._connect() as db:
            db.execute(
                "INSERT INTO automations VALUES (?, ?, ?, ?, 0, ?, ?)",
                (item_id, name, prompt, interval_minutes, now, now),
            )
        return self.get(item_id)

    def list(self) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM automations ORDER BY created_at DESC").fetchall()
        return [self._serialize(row) for row in rows]

    def get(self, item_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM automations WHERE id = ?", (item_id,)).fetchone()
        return self._serialize(row) if row else None

    def set_enabled(self, item_id: str, enabled: bool) -> dict | None:
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE automations SET enabled = ?, updated_at = ? WHERE id = ?",
                (int(enabled), datetime.now(timezone.utc).isoformat(), item_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get(item_id)

    def delete(self, item_id: str) -> bool:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM automations WHERE id = ?", (item_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _serialize(row) -> dict:
        return {**dict(row), "enabled": bool(row["enabled"])}
