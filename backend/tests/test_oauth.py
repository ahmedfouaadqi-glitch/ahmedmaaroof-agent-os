import asyncio
import json
import sqlite3
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet

from app.services.oauth import OAuthConnector, OAuthError


def make_settings(tmp_path):
    return SimpleNamespace(
        oauth_token_encryption_key=Fernet.generate_key().decode(),
        email_oauth_authorization_url="https://identity.example.test/oauth/authorize",
        email_oauth_token_url="https://identity.example.test/oauth/token",
        email_oauth_client_id="agent-client",
        email_oauth_client_secret="server-secret",
        email_oauth_redirect_uri="https://agent.example.test/v1/oauth/email/callback",
        email_oauth_scopes="openid email.read",
        calendar_oauth_authorization_url="https://identity.example.test/oauth/authorize",
        calendar_oauth_token_url="https://identity.example.test/oauth/token",
        calendar_oauth_client_id="agent-client",
        calendar_oauth_client_secret="server-secret",
        calendar_oauth_redirect_uri="https://agent.example.test/v1/oauth/calendar/callback",
        calendar_oauth_scopes="calendar.read",
    )


def test_oauth_authorization_uses_state_and_pkce(tmp_path):
    service = OAuthConnector(tmp_path / "oauth.sqlite3", make_settings(tmp_path))
    result = service.create_authorization("email")
    query = parse_qs(urlsplit(result["authorization_url"]).query)
    assert result["expires_in"] == 600
    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert len(query["state"][0]) >= 32
    assert len(query["code_challenge"][0]) == 43


def test_oauth_callback_exchanges_code_and_encrypts_tokens(tmp_path):
    settings = make_settings(tmp_path)
    db_path = tmp_path / "oauth.sqlite3"
    seen = {}

    def handler(request):
        seen["form"] = dict(parse_qs(request.content.decode()))
        return httpx.Response(200, json={
            "access_token": "sensitive-access-token",
            "refresh_token": "sensitive-refresh-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid email.read",
        })

    service = OAuthConnector(db_path, settings, transport=httpx.MockTransport(handler))
    authorization = service.create_authorization("email")
    state = parse_qs(urlsplit(authorization["authorization_url"]).query)["state"][0]
    result = asyncio.run(service.complete_authorization("email", "authorization-code", state))

    assert result["connected"] is True
    assert result["scopes"] == ["openid", "email.read"]
    assert seen["form"]["grant_type"] == ["authorization_code"]
    assert seen["form"]["code_verifier"]
    assert seen["form"]["client_secret"] == ["server-secret"]
    with sqlite3.connect(db_path) as db:
        ciphertext = db.execute(
            "SELECT token_ciphertext FROM oauth_connections WHERE integration='email'"
        ).fetchone()[0]
    assert "sensitive-access-token" not in ciphertext
    assert "sensitive-refresh-token" not in ciphertext


def test_oauth_state_is_one_time_use(tmp_path):
    service = OAuthConnector(
        tmp_path / "oauth.sqlite3",
        make_settings(tmp_path),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"access_token": "x"})),
    )
    auth = service.create_authorization("calendar")
    state = parse_qs(urlsplit(auth["authorization_url"]).query)["state"][0]
    asyncio.run(service.complete_authorization("calendar", "code", state))
    with pytest.raises(OAuthError, match="invalid, expired or already used"):
        asyncio.run(service.complete_authorization("calendar", "code", state))


def test_oauth_fails_closed_without_encryption_key(tmp_path):
    settings = make_settings(tmp_path)
    settings.oauth_token_encryption_key = ""
    service = OAuthConnector(tmp_path / "oauth.sqlite3", settings)
    with pytest.raises(OAuthError, match="encryption is not configured"):
        service.create_authorization("email")


def test_oauth_rejects_unknown_integrations(tmp_path):
    service = OAuthConnector(tmp_path / "oauth.sqlite3", make_settings(tmp_path))
    with pytest.raises(OAuthError, match="Unsupported"):
        service.create_authorization("drive")


def test_expired_access_token_is_refreshed_and_rotated(tmp_path):
    settings = make_settings(tmp_path)
    db_path = tmp_path / "oauth.sqlite3"
    calls = []

    def handler(request):
        form = dict(parse_qs(request.content.decode()))
        calls.append(form.get("grant_type", [""])[0])
        if form.get("grant_type") == ["authorization_code"]:
            return httpx.Response(200, json={
                "access_token": "first-access",
                "refresh_token": "stable-refresh",
                "expires_in": 3600,
                "scope": "openid email.read",
            })
        return httpx.Response(200, json={
            "access_token": "rotated-access",
            "expires_in": 3600,
        })

    service = OAuthConnector(db_path, settings, transport=httpx.MockTransport(handler))
    auth = service.create_authorization("email")
    state = parse_qs(urlsplit(auth["authorization_url"]).query)["state"][0]
    asyncio.run(service.complete_authorization("email", "code", state))
    with sqlite3.connect(db_path) as db:
        db.execute(
            "UPDATE oauth_connections SET expires_at = ? WHERE integration = 'email'",
            ("2000-01-01T00:00:00+00:00",),
        )
    access = asyncio.run(service.access_token("email"))
    assert access == "rotated-access"
    assert calls == ["authorization_code", "refresh_token"]
    assert service.status("email")["connected"] is True


def test_oauth_api_routes_are_registered():
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/v1/oauth/{integration}/start" in paths
    assert "/v1/oauth/{integration}/callback" in paths
    assert "/v1/oauth/{integration}/status" in paths
    assert "/v1/oauth/{integration}" in paths
