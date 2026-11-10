from __future__ import annotations

import base64
import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

import httpx
from cryptography.fernet import Fernet, InvalidToken


class OAuthError(RuntimeError):
    pass


class OAuthConnector:
    """Provider-neutral OAuth 2.0 authorization-code + PKCE foundation.

    Provider API access is intentionally separate: this class only handles consent,
    one-time state validation and encrypted token persistence.
    """

    INTEGRATIONS = ("email", "calendar")

    def __init__(self, database_path: Path, settings, transport: httpx.AsyncBaseTransport | None = None):
        self.database_path = database_path
        self.settings = settings
        self.transport = transport
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS oauth_states (
                    state_hash TEXT PRIMARY KEY,
                    integration TEXT NOT NULL,
                    verifier_ciphertext TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS oauth_connections (
                    integration TEXT PRIMARY KEY,
                    token_ciphertext TEXT NOT NULL,
                    scopes TEXT NOT NULL,
                    expires_at TEXT,
                    connected_at TEXT NOT NULL
                )
            """)

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def _fernet(self) -> Fernet:
        key = self.settings.oauth_token_encryption_key
        if not key:
            raise OAuthError("OAuth token encryption is not configured")
        try:
            return Fernet(key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise OAuthError("OAuth token encryption key must be a valid Fernet key") from exc

    def _config(self, integration: str) -> dict[str, str]:
        if integration not in self.INTEGRATIONS:
            raise OAuthError("Unsupported OAuth integration")
        prefix = integration.lower() + "_oauth_"
        fields = {
            "authorization_url": getattr(self.settings, prefix + "authorization_url", ""),
            "token_url": getattr(self.settings, prefix + "token_url", ""),
            "client_id": getattr(self.settings, prefix + "client_id", ""),
            "client_secret": getattr(self.settings, prefix + "client_secret", ""),
            "redirect_uri": getattr(self.settings, prefix + "redirect_uri", ""),
            "scopes": getattr(self.settings, prefix + "scopes", ""),
        }
        missing = [name for name, value in fields.items() if not value]
        if missing:
            raise OAuthError("OAuth integration is not configured: " + ", ".join(missing))
        if urlsplit(fields["authorization_url"]).scheme != "https" or urlsplit(fields["token_url"]).scheme != "https":
            raise OAuthError("OAuth authorization and token endpoints must use HTTPS")
        return fields

    def status(self, integration: str) -> dict:
        if integration not in self.INTEGRATIONS:
            raise OAuthError("Unsupported OAuth integration")
        with self._connect() as db:
            row = db.execute(
                "SELECT scopes, expires_at, connected_at FROM oauth_connections WHERE integration = ?",
                (integration,),
            ).fetchone()
        return {
            "integration": integration,
            "connected": row is not None,
            "scopes": row["scopes"].split() if row else [],
            "expires_at": row["expires_at"] if row else None,
            "connected_at": row["connected_at"] if row else None,
        }


    async def access_token(self, integration: str) -> str:
        """Return a usable access token, refreshing it shortly before expiry."""
        if integration not in self.INTEGRATIONS:
            raise OAuthError("Unsupported OAuth integration")
        with self._connect() as db:
            row = db.execute(
                "SELECT token_ciphertext, expires_at FROM oauth_connections WHERE integration = ?",
                (integration,),
            ).fetchone()
        if row is None:
            raise OAuthError("OAuth integration is not authorized")
        fernet = self._fernet()
        try:
            token_data = json.loads(fernet.decrypt(row["token_ciphertext"].encode()).decode())
        except (InvalidToken, ValueError, TypeError) as exc:
            raise OAuthError("Stored OAuth token could not be decrypted") from exc
        expires_at = datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
        if expires_at is None or expires_at > datetime.now(timezone.utc) + timedelta(seconds=60):
            return token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise OAuthError("OAuth access token expired and no refresh token is available")
        config = self._config(integration)
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
        }
        async with httpx.AsyncClient(timeout=20, transport=self.transport) as client:
            response = await client.post(
                config["token_url"], data=payload, headers={"Accept": "application/json"}
            )
        if response.is_error:
            raise OAuthError(f"OAuth token refresh returned HTTP {response.status_code}")
        try:
            refreshed = response.json()
        except ValueError as exc:
            raise OAuthError("OAuth refresh endpoint returned invalid JSON") from exc
        if not isinstance(refreshed, dict) or not isinstance(refreshed.get("access_token"), str):
            raise OAuthError("OAuth refresh response is missing access_token")
        merged = {**token_data, **refreshed}
        merged.setdefault("refresh_token", refresh_token)
        expires_in = refreshed.get("expires_in")
        new_expiry = (
            (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()
            if isinstance(expires_in, (int, float)) and expires_in > 0
            else None
        )
        encrypted = fernet.encrypt(json.dumps(merged, separators=(",", ":")).encode()).decode()
        with self._connect() as db:
            db.execute(
                "UPDATE oauth_connections SET token_ciphertext = ?, expires_at = ? WHERE integration = ?",
                (encrypted, new_expiry, integration),
            )
        return merged["access_token"]

    def disconnect(self, integration: str) -> bool:
        if integration not in self.INTEGRATIONS:
            raise OAuthError("Unsupported OAuth integration")
        with self._connect() as db:
            cursor = db.execute("DELETE FROM oauth_connections WHERE integration = ?", (integration,))
            return cursor.rowcount > 0

    def create_authorization(self, integration: str) -> dict:
        config = self._config(integration)
        fernet = self._fernet()
        now = datetime.now(timezone.utc)
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        state_hash = hashlib.sha256(state.encode()).hexdigest()
        with self._connect() as db:
            db.execute("DELETE FROM oauth_states WHERE expires_at <= ?", (now.isoformat(),))
            db.execute(
                """INSERT INTO oauth_states
                   (state_hash, integration, verifier_ciphertext, expires_at, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    state_hash,
                    integration,
                    fernet.encrypt(verifier.encode()).decode(),
                    (now + timedelta(minutes=10)).isoformat(),
                    now.isoformat(),
                ),
            )
        params = {
            "response_type": "code",
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "scope": config["scopes"],
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        parts = urlsplit(config["authorization_url"])
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.update(params)
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
        return {"authorization_url": url, "expires_in": 600}

    async def complete_authorization(self, integration: str, code: str, state: str) -> dict:
        config = self._config(integration)
        fernet = self._fernet()
        state_hash = hashlib.sha256(state.encode()).hexdigest()
        now = datetime.now(timezone.utc)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM oauth_states WHERE state_hash = ? AND integration = ?",
                (state_hash, integration),
            ).fetchone()
            if row is None:
                db.rollback()
                raise OAuthError("OAuth state is invalid, expired or already used")
            db.execute("DELETE FROM oauth_states WHERE state_hash = ?", (state_hash,))
            db.commit()
        if datetime.fromisoformat(row["expires_at"]) <= now:
            raise OAuthError("OAuth state has expired")
        try:
            verifier = fernet.decrypt(row["verifier_ciphertext"].encode()).decode()
        except InvalidToken as exc:
            raise OAuthError("OAuth PKCE verifier could not be decrypted") from exc
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config["redirect_uri"],
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code_verifier": verifier,
        }
        async with httpx.AsyncClient(timeout=20, transport=self.transport) as client:
            response = await client.post(
                config["token_url"],
                data=payload,
                headers={"Accept": "application/json"},
            )
        if response.is_error:
            raise OAuthError(f"OAuth token endpoint returned HTTP {response.status_code}")
        try:
            token_data = response.json()
        except ValueError as exc:
            raise OAuthError("OAuth token endpoint returned invalid JSON") from exc
        if not isinstance(token_data, dict) or not isinstance(token_data.get("access_token"), str):
            raise OAuthError("OAuth token response is missing access_token")
        scopes = token_data.get("scope") or config["scopes"]
        if isinstance(scopes, list):
            scopes = " ".join(str(scope) for scope in scopes)
        if not isinstance(scopes, str):
            scopes = config["scopes"]
        expires_in = token_data.get("expires_in")
        expires_at = None
        if isinstance(expires_in, (int, float)) and expires_in > 0:
            expires_at = (now + timedelta(seconds=int(expires_in))).isoformat()
        encrypted = fernet.encrypt(json.dumps(token_data, separators=(",", ":")).encode()).decode()
        with self._connect() as db:
            db.execute(
                """INSERT INTO oauth_connections
                   (integration, token_ciphertext, scopes, expires_at, connected_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(integration) DO UPDATE SET
                     token_ciphertext = excluded.token_ciphertext,
                     scopes = excluded.scopes,
                     expires_at = excluded.expires_at,
                     connected_at = excluded.connected_at""",
                (integration, encrypted, scopes, expires_at, now.isoformat()),
            )
        return self.status(integration)
