import sqlite3
import time

from app.services.rate_limiter import SQLiteRateLimiter


def test_rate_limiter_enforces_window_and_returns_retry_after(tmp_path):
    database = tmp_path / "limits.sqlite3"
    limiter = SQLiteRateLimiter(database)
    assert limiter.consume("client-secret-identifier", 2, 60) == (True, 0)
    assert limiter.consume("client-secret-identifier", 2, 60) == (True, 0)
    allowed, retry_after = limiter.consume("client-secret-identifier", 2, 60)
    assert allowed is False
    assert 1 <= retry_after <= 60
    with sqlite3.connect(database) as db:
        bucket = db.execute("SELECT bucket_hash FROM rate_limit_buckets").fetchone()[0]
    assert "client-secret-identifier" not in bucket


def test_rate_limiter_resets_expired_window(tmp_path):
    database = tmp_path / "limits.sqlite3"
    limiter = SQLiteRateLimiter(database)
    limiter.consume("client-a", 1, 60)
    with sqlite3.connect(database) as db:
        db.execute(
            "UPDATE rate_limit_buckets SET window_started = ?",
            (time.time() - 120,),
        )
    assert limiter.consume("client-a", 1, 60) == (True, 0)
