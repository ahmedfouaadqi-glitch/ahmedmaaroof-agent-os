import asyncio
import base64
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit, parse_qs
import json

import httpx
import pytest

from app.services.designer import DesignerError, DesignerService


def make_settings(tmp_path):
    return SimpleNamespace(
        designer_provider_endpoint="https://images.example.test/v1/images/generations",
        image_provider_api_key="server-only-key",
        designer_provider_model="image-model-test",
        designer_cost_per_image_usd=0.04,
        designer_max_cost_usd=0.10,
    )


def png_bytes():
    return b"\x89PNG\r\n\x1a\n" + b"test-image-data"


def test_estimate_requires_configured_provider_and_budget(tmp_path):
    settings = make_settings(tmp_path)
    settings.designer_max_cost_usd = 0
    service = DesignerService(tmp_path / "agent.sqlite3", tmp_path / "artifacts", settings)
    with pytest.raises(DesignerError, match="budget"):
        service.estimate("A calm landscape", "1024x1024")


def test_generation_requires_approval_and_stores_local_artifact(tmp_path):
    settings = make_settings(tmp_path)
    image = png_bytes()
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        assert request.headers["authorization"] == "Bearer server-only-key"
        return httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(image).decode()}]})

    service = DesignerService(
        tmp_path / "agent.sqlite3", tmp_path / "artifacts", settings,
        transport=httpx.MockTransport(handler),
    )
    prompt = "A quiet mountain lake at sunrise"
    estimate = service.estimate(prompt, "1024x1024")
    assert estimate["approval_required"] is True
    assert estimate["estimated_cost_usd"] == 0.04
    assert requests == []

    result = asyncio.run(service.generate(prompt, "1024x1024", estimate["approval_id"]))
    assert result["mime_type"] == "image/png"
    assert result["estimated_cost_usd"] == 0.04
    path, media_type = service.artifact_path(result["id"])
    assert path.read_bytes() == image
    assert media_type == "image/png"
    assert service.history()[0]["id"] == result["id"]
    assert requests[0]["model"] == "image-model-test"
    assert requests[0]["response_format"] == "b64_json"

    with pytest.raises(DesignerError, match="already used"):
        asyncio.run(service.generate(prompt, "1024x1024", estimate["approval_id"]))


def test_approval_is_bound_to_prompt_and_size(tmp_path):
    service = DesignerService(tmp_path / "agent.sqlite3", tmp_path / "artifacts", make_settings(tmp_path))
    approval = service.estimate("Approved prompt", "1024x1024")
    with pytest.raises(DesignerError, match="differs from the approved request"):
        asyncio.run(service.generate("Different prompt", "1024x1024", approval["approval_id"]))


def test_provider_endpoint_rejects_insecure_remote_http(tmp_path):
    settings = make_settings(tmp_path)
    settings.designer_provider_endpoint = "http://remote.example.test/generate"
    service = DesignerService(tmp_path / "agent.sqlite3", tmp_path / "artifacts", settings)
    with pytest.raises(DesignerError, match="HTTPS"):
        service.estimate("A secure prompt", "1024x1024")


def test_designer_routes_are_registered():
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/v1/designer/estimate" in paths
    assert "/v1/designer/generate" in paths
    assert "/v1/designer/history" in paths
    assert "/v1/designer/artifacts/{artifact_id}" in paths
