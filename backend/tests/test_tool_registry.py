import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.tool_registry import ToolError, build_default_registry


class MemoryStub:
    def search(self, query, limit=6):
        return [{"title": "Example", "query": query, "limit": limit}]


class AutomationStub:
    def list(self):
        return [{"id": "auto-1", "enabled": False}]


def test_registry_exposes_allowlisted_tools_and_disabled_high_risk():
    registry = build_default_registry(Path("unused.sqlite3"))
    tools = {tool["id"]: tool for tool in registry.list_tools()}
    assert tools["memory.search"]["enabled"] is True
    assert tools["automations.list"]["enabled"] is True
    assert tools["email.send"]["enabled"] is False
    assert tools["calendar.create_event"]["requires_approval"] is True
    assert tools["system.admin"]["risk"] == "critical"


def test_read_only_tool_executes_and_writes_redacted_audit(tmp_path):
    registry = build_default_registry(tmp_path / "agent.sqlite3")
    result = asyncio.run(registry.execute(
        "memory.search",
        {"query": "private search phrase", "limit": 3},
        {"memory": MemoryStub(), "automations": AutomationStub(), "integrations": lambda: []},
    ))
    assert result["status"] == "completed"
    assert result["result"][0]["query"] == "private search phrase"
    audit = registry.audit()
    assert len(audit) == 1
    assert audit[0]["status"] == "completed"
    assert "private search phrase" not in audit[0]["input_digest"]
    assert audit[0]["result_summary"]


def test_invalid_tool_arguments_are_rejected_and_audited(tmp_path):
    registry = build_default_registry(tmp_path / "agent.sqlite3")
    with pytest.raises(ToolError, match="schema validation"):
        asyncio.run(registry.execute(
            "memory.search",
            {"query": "", "limit": 500},
            {"memory": MemoryStub()},
        ))
    assert registry.audit()[0]["status"] == "failed"
    assert registry.audit()[0]["error_code"] == "validation_error"


def test_disabled_high_risk_tool_cannot_execute(tmp_path):
    registry = build_default_registry(tmp_path / "agent.sqlite3")
    with pytest.raises(ToolError, match="disabled"):
        asyncio.run(registry.execute("email.send", {}, {}))
    with pytest.raises(ToolError, match="disabled"):
        asyncio.run(registry.execute("system.admin", {}, {}))


def test_tool_routes_are_registered():
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/v1/tools" in paths
    assert "/v1/tools/{tool_id}/execute" in paths
    assert "/v1/tools/audit" in paths
