from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path


class SQLiteRateLimiter:
    """Persistent fixed-window rate limiter keyed by hashed client identifiers."""

    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS rate_limit_buckets (
                    bucket_hash TEXT PRIMARY KEY,
                    window_started REAL NOT NULL,
                    request_count INTEGER NOT NULL
                )
            """)

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=10)
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def consume(self, identifier: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        bucket = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT window_started, request_count FROM rate_limit_buckets WHERE bucket_hash = ?",
                (bucket,),
            ).fetchone()
            if row is None or now - row[0] >= window_seconds:
                db.execute(
                    """INSERT INTO rate_limit_buckets (bucket_hash, window_started, request_count)
                       VALUES (?, ?, 1) ON CONFLICT(bucket_hash) DO UPDATE SET
                       window_started = excluded.window_started, request_count = 1""",
                    (bucket, now),
                )
                allowed, retry_after = True, 0
            elif row[1] >= limit:
                allowed = False
                retry_after = max(1, int(window_seconds - (now - row[0])))
            else:
                db.execute(
                    "UPDATE rate_limit_buckets SET request_count = request_count + 1 WHERE bucket_hash = ?",
                    (bucket,),
                )
                allowed, retry_after = True, 0
            db.execute(
                "DELETE FROM rate_limit_buckets WHERE window_started < ?",
                (now - window_seconds * 2,),
            )
            db.commit()
        return allowed, retry_after
