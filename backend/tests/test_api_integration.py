from fastapi.testclient import TestClient

import app.main as main


# End-to-end API smoke coverage for the configured personal workspace.
def test_api_integration_smoke_and_security_headers(tmp_path, monkeypatch):
    monkeypatch.setattr(main.settings, "database_path", tmp_path / "agent.sqlite3")
    monkeypatch.setattr(main.settings, "vault_path", tmp_path / "vault")
    monkeypatch.setattr(main.settings, "designer_output_dir", tmp_path / "designer")
    main.app.dependency_overrides[main.require_api_key] = lambda: "authenticated"

    try:
        with TestClient(main.app) as client:
            health = client.get("/v1/health")
            assert health.status_code == 200
            assert health.headers["x-content-type-options"] == "nosniff"
            assert health.headers["x-frame-options"] == "DENY"
            assert health.headers["referrer-policy"] == "strict-origin-when-cross-origin"

            catalog = client.get("/v1/tools")
            assert catalog.status_code == 200
            assert "memory.search" in {tool["id"] for tool in catalog.json()["tools"]}

            execution = client.post(
                "/v1/tools/memory.search/execute",
                json={"arguments": {"query": "nothing indexed", "limit": 5}},
            )
            assert execution.status_code == 200
            assert execution.json()["status"] == "completed"

            audit = client.get("/v1/tools/audit")
            assert audit.status_code == 200
            assert audit.json()["executions"][0]["status"] == "completed"

            automation = client.post(
                "/v1/automations",
                json={"name": "Test schedule", "prompt": "Summarize system status", "interval_minutes": 60},
            )
            assert automation.status_code == 200
            listing = client.get("/v1/automations")
            assert listing.status_code == 200
            assert listing.json()["automations"][0]["name"] == "Test schedule"

            voice = client.get("/v1/voice/status")
            assert voice.status_code == 200
            assert voice.json()["whisper"]["configured"] is False

            designer = client.post(
                "/v1/designer/estimate",
                json={"prompt": "A minimal geometric poster", "size": "1024x1024"},
            )
            assert designer.status_code == 503

            oauth = client.post("/v1/oauth/email/start")
            assert oauth.status_code == 503

            oversized = client.get("/v1/health", headers={"Content-Length": str(main.settings.max_body_bytes + 1)})
            assert oversized.status_code == 413
    finally:
        main.app.dependency_overrides.pop(main.require_api_key, None)
