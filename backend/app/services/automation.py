from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(value: datetime) -> str:
    return value.isoformat()


class AutomationStore:
    """SQLite-backed automation definitions, leases and execution history."""

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
            columns = {row["name"] for row in db.execute("PRAGMA table_info(automations)")}
            for name, definition in (
                ("next_run_at", "TEXT"),
                ("lease_until", "TEXT"),
                ("failure_count", "INTEGER NOT NULL DEFAULT 0"),
            ):
                if name not in columns:
                    db.execute(f"ALTER TABLE automations ADD COLUMN {name} {definition}")
            db.execute("""
                CREATE TABLE IF NOT EXISTS automation_executions (
                    id TEXT PRIMARY KEY,
                    automation_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    answer TEXT,
                    error TEXT,
                    FOREIGN KEY (automation_id) REFERENCES automations(id) ON DELETE CASCADE
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_automation_due ON automations(enabled, next_run_at)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_execution_automation ON automation_executions(automation_id, started_at DESC)")

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def create(self, name: str, prompt: str, interval_minutes: int) -> dict:
        now = _stamp(_now())
        item_id = str(uuid4())
        with self._connect() as db:
            db.execute(
                """INSERT INTO automations
                   (id, name, prompt, interval_minutes, enabled, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 0, ?, ?)""",
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
        now = _now()
        next_run = _stamp(now + timedelta(minutes=self.get(item_id)["interval_minutes"])) if enabled and self.get(item_id) else None
        with self._connect() as db:
            cursor = db.execute(
                """UPDATE automations
                   SET enabled = ?, updated_at = ?, next_run_at = ?, lease_until = NULL,
                       failure_count = CASE WHEN ? = 1 THEN 0 ELSE failure_count END
                   WHERE id = ?""",
                (int(enabled), _stamp(now), next_run, int(enabled), item_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get(item_id)

    def delete(self, item_id: str) -> bool:
        with self._connect() as db:
            db.execute("PRAGMA foreign_keys = ON")
            cursor = db.execute("DELETE FROM automations WHERE id = ?", (item_id,))
            return cursor.rowcount > 0

    def claim_due(self, lease_seconds: int = 180) -> dict | None:
        """Atomically lease one due automation; safe against competing worker processes."""
        now = _now()
        now_text = _stamp(now)
        lease_text = _stamp(now + timedelta(seconds=lease_seconds))
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT * FROM automations
                   WHERE enabled = 1 AND next_run_at IS NOT NULL AND next_run_at <= ?
                     AND (lease_until IS NULL OR lease_until <= ?)
                   ORDER BY next_run_at ASC LIMIT 1""",
                (now_text, now_text),
            ).fetchone()
            if row is None:
                db.commit()
                return None
            execution_id = str(uuid4())
            updated = db.execute(
                """UPDATE automations SET lease_until = ?
                   WHERE id = ? AND enabled = 1
                     AND (lease_until IS NULL OR lease_until <= ?)""",
                (lease_text, row["id"], now_text),
            )
            if updated.rowcount != 1:
                db.rollback()
                return None
            db.execute(
                """INSERT INTO automation_executions
                   (id, automation_id, status, started_at)
                   VALUES (?, ?, 'running', ?)""",
                (execution_id, row["id"], now_text),
            )
            db.commit()
            return {**self._serialize(row), "execution_id": execution_id}

    def finish(self, automation_id: str, execution_id: str, answer: str) -> None:
        now = _now()
        with self._connect() as db:
            db.execute(
                """UPDATE automation_executions
                   SET status = 'completed', finished_at = ?, answer = ?
                   WHERE id = ? AND status = 'running'""",
                (_stamp(now), answer[:12000], execution_id),
            )
            db.execute(
                """UPDATE automations SET lease_until = NULL, failure_count = 0,
                   next_run_at = CASE WHEN enabled = 1
                     THEN ? ELSE NULL END, updated_at = ? WHERE id = ?""",
                (_stamp(now + timedelta(minutes=self._interval(db, automation_id))), _stamp(now), automation_id),
            )

    def fail(self, automation_id: str, execution_id: str, error: str, max_retries: int = 2) -> None:
        now = _now()
        with self._connect() as db:
            db.execute(
                """UPDATE automation_executions
                   SET status = 'failed', finished_at = ?, error = ?
                   WHERE id = ? AND status = 'running'""",
                (_stamp(now), error[:4000], execution_id),
            )
            row = db.execute("SELECT interval_minutes, failure_count, enabled FROM automations WHERE id = ?", (automation_id,)).fetchone()
            if row is None:
                return
            failures = row["failure_count"] + 1
            delay = min(5 * failures, 60) if failures <= max_retries else row["interval_minutes"]
            next_run = _stamp(now + timedelta(minutes=delay)) if row["enabled"] else None
            db.execute(
                """UPDATE automations SET lease_until = NULL, failure_count = ?,
                   next_run_at = ?, updated_at = ? WHERE id = ?""",
                (failures, next_run, _stamp(now), automation_id),
            )

    @staticmethod
    def _interval(db, automation_id: str) -> int:
        row = db.execute("SELECT interval_minutes FROM automations WHERE id = ?", (automation_id,)).fetchone()
        return row["interval_minutes"] if row else 60

    def executions(self, automation_id: str, limit: int = 20) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                """SELECT * FROM automation_executions WHERE automation_id = ?
                   ORDER BY started_at DESC LIMIT ?""",
                (automation_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _serialize(row) -> dict:
        item = dict(row)
        item["enabled"] = bool(item["enabled"])
        return item
