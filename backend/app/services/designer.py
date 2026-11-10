from __future__ import annotations

import base64
import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx


class DesignerError(RuntimeError):
    pass


class DesignerService:
    """Approval-gated OpenAI-compatible image generation with local artifact storage."""

    SIZES = {"1024x1024", "1024x1536", "1536x1024"}

    def __init__(self, database_path: Path, output_dir: Path, settings, transport: httpx.AsyncBaseTransport | None = None):
        self.database_path = database_path
        self.output_dir = output_dir
        self.settings = settings
        self.transport = transport
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS designer_approvals (
                    approval_hash TEXT PRIMARY KEY,
                    prompt_hash TEXT NOT NULL,
                    size TEXT NOT NULL,
                    estimated_cost_usd REAL NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    used_at TEXT
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS designer_generations (
                    id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    model TEXT NOT NULL,
                    size TEXT NOT NULL,
                    estimated_cost_usd REAL NOT NULL,
                    artifact_filename TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def _provider(self) -> tuple[str, str, str, float]:
        endpoint = self.settings.designer_provider_endpoint
        api_key = self.settings.image_provider_api_key
        model = self.settings.designer_provider_model
        unit_cost = float(self.settings.designer_cost_per_image_usd)
        max_cost = float(self.settings.designer_max_cost_usd)
        if not endpoint or not api_key or not model:
            raise DesignerError("Designer provider is not configured")
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            raise DesignerError("Designer provider endpoint must use HTTPS")
        if unit_cost <= 0 or max_cost <= 0:
            raise DesignerError("Designer cost and maximum budget must be explicitly configured")
        if unit_cost > max_cost:
            raise DesignerError("Estimated image cost exceeds the configured per-request budget")
        return endpoint, api_key, model, unit_cost

    @staticmethod
    def _prompt_hash(prompt: str) -> str:
        return hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()

    def estimate(self, prompt: str, size: str) -> dict:
        if not prompt.strip():
            raise DesignerError("Prompt is required")
        if size not in self.SIZES:
            raise DesignerError("Unsupported image size")
        _, _, model, unit_cost = self._provider()
        now = datetime.now(timezone.utc)
        approval = secrets.token_urlsafe(32)
        approval_hash = hashlib.sha256(approval.encode()).hexdigest()
        with self._connect() as db:
            db.execute("DELETE FROM designer_approvals WHERE expires_at <= ?", (now.isoformat(),))
            db.execute(
                """INSERT INTO designer_approvals
                   (approval_hash, prompt_hash, size, estimated_cost_usd, expires_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    approval_hash,
                    self._prompt_hash(prompt),
                    size,
                    unit_cost,
                    (now + timedelta(minutes=10)).isoformat(),
                    now.isoformat(),
                ),
            )
        return {
            "approval_id": approval,
            "model": model,
            "size": size,
            "estimated_cost_usd": unit_cost,
            "expires_in": 600,
            "approval_required": True,
        }

    async def generate(self, prompt: str, size: str, approval_id: str) -> dict:
        endpoint, api_key, model, unit_cost = self._provider()
        if size not in self.SIZES:
            raise DesignerError("Unsupported image size")
        approval_hash = hashlib.sha256(approval_id.encode()).hexdigest()
        now = datetime.now(timezone.utc)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM designer_approvals WHERE approval_hash = ?",
                (approval_hash,),
            ).fetchone()
            if row is None or row["used_at"] is not None:
                db.rollback()
                raise DesignerError("Approval is invalid or already used")
            if datetime.fromisoformat(row["expires_at"]) <= now:
                db.execute("DELETE FROM designer_approvals WHERE approval_hash = ?", (approval_hash,))
                db.commit()
                raise DesignerError("Approval has expired")
            if row["prompt_hash"] != self._prompt_hash(prompt) or row["size"] != size:
                db.rollback()
                raise DesignerError("Prompt or size differs from the approved request")
            if row["estimated_cost_usd"] != unit_cost or row["estimated_cost_usd"] > float(self.settings.designer_max_cost_usd):
                db.rollback()
                raise DesignerError("Approved cost no longer matches the configured budget")
            db.execute(
                "UPDATE designer_approvals SET used_at = ? WHERE approval_hash = ?",
                (now.isoformat(), approval_hash),
            )
            db.commit()

        payload = {
            "model": model,
            "prompt": prompt.strip(),
            "size": size,
            "n": 1,
            "response_format": "b64_json",
        }
        async with httpx.AsyncClient(timeout=120, transport=self.transport) as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers={"Authorization": "Bearer " + api_key, "Accept": "application/json"},
            )
        if response.is_error:
            raise DesignerError(f"Designer provider returned HTTP {response.status_code}")
        try:
            data = response.json()
            encoded = data["data"][0]["b64_json"]
            image_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            raise DesignerError("Designer provider must return data[0].b64_json") from exc
        if not image_bytes or len(image_bytes) > 20 * 1024 * 1024:
            raise DesignerError("Generated image is empty or exceeds 20 MB")
        mime_type = self._detect_mime(image_bytes)
        if mime_type is None:
            raise DesignerError("Generated artifact is not a supported PNG, JPEG or WebP image")
        artifact_id = str(uuid4())
        extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[mime_type]
        filename = artifact_id + "." + extension
        (self.output_dir / filename).write_bytes(image_bytes)
        with self._connect() as db:
            db.execute(
                """INSERT INTO designer_generations
                   (id, prompt, model, size, estimated_cost_usd, artifact_filename, mime_type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (artifact_id, prompt.strip(), model, size, unit_cost, filename, mime_type, now.isoformat()),
            )
        return {
            "id": artifact_id,
            "model": model,
            "size": size,
            "estimated_cost_usd": unit_cost,
            "mime_type": mime_type,
            "artifact_url": f"/v1/designer/artifacts/{artifact_id}",
            "created_at": now.isoformat(),
        }

    @staticmethod
    def _detect_mime(data: bytes) -> str | None:
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "image/webp"
        return None

    def artifact_path(self, artifact_id: str) -> tuple[Path, str] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT artifact_filename, mime_type FROM designer_generations WHERE id = ?",
                (artifact_id,),
            ).fetchone()
        if row is None:
            return None
        path = self.output_dir / row["artifact_filename"]
        if not path.is_file():
            return None
        return path, row["mime_type"]

    def history(self, limit: int = 20) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                """SELECT id, prompt, model, size, estimated_cost_usd, mime_type, created_at
                   FROM designer_generations ORDER BY created_at DESC LIMIT ?""",
                (max(1, min(limit, 100)),),
            ).fetchall()
        return [
            {**dict(row), "artifact_url": f"/v1/designer/artifacts/{row['id']}"}
            for row in rows
        ]
