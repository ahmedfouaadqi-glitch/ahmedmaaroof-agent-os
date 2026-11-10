from datetime import datetime, timezone
from pathlib import Path
import sqlite3


class WorkspaceStore:
    """Workspace registry. Identity and membership are intentionally separate."""

    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL
                )
            """)

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def ensure_default(self, workspace_id: str, name: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute(
                """INSERT INTO workspaces (id, name, status, created_at)
                   VALUES (?, ?, 'active', ?)
                   ON CONFLICT(id) DO NOTHING""",
                (workspace_id, name, now),
            )
            row = db.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
        return dict(row)

    def get(self, workspace_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
        return dict(row) if row else None
