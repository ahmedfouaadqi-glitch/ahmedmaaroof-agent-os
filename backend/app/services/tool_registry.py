from __future__ import annotations

import hashlib
import inspect
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ToolError(RuntimeError):
    pass


class EmptyToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MemorySearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=6, ge=1, le=20)


@dataclass(frozen=True)
class ToolSpec:
    id: str
    name: str
    description: str
    risk: str
    enabled: bool
    requires_approval: bool
    input_model: type[BaseModel]
    handler: Callable[[BaseModel, dict[str, Any]], Any] | None = None


class ToolRegistry:
    """Allowlisted tool catalog with strict input contracts and persistent audit metadata."""

    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._tools: dict[str, ToolSpec] = {}
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS tool_executions (
                    id TEXT PRIMARY KEY,
                    tool_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_digest TEXT NOT NULL,
                    result_summary TEXT,
                    error_code TEXT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT
                )
            """)

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def register(self, spec: ToolSpec) -> None:
        if spec.id in self._tools:
            raise ValueError(f"Tool already registered: {spec.id}")
        if spec.enabled and spec.handler is None:
            raise ValueError("Enabled tools require a handler")
        self._tools[spec.id] = spec

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "id": spec.id,
                "name": spec.name,
                "description": spec.description,
                "risk": spec.risk,
                "enabled": spec.enabled,
                "requires_approval": spec.requires_approval,
                "input_schema": spec.input_model.model_json_schema(),
            }
            for spec in self._tools.values()
        ]

    async def execute(self, tool_id: str, arguments: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        spec = self._tools.get(tool_id)
        execution_id = str(uuid4())
        started = datetime.now(timezone.utc).isoformat()
        digest = hashlib.sha256(
            json.dumps(arguments, sort_keys=True, ensure_ascii=False, default=str).encode()
        ).hexdigest()
        with self._connect() as db:
            db.execute(
                """INSERT INTO tool_executions
                   (id, tool_id, status, input_digest, started_at)
                   VALUES (?, ?, 'running', ?, ?)""",
                (execution_id, tool_id, digest, started),
            )

        denied_reason = None
        if spec is None:
            denied_reason = "unknown_tool"
            message = "Unknown tool"
        elif not spec.enabled or spec.handler is None:
            denied_reason = "disabled"
            message = "Tool is disabled"
        elif spec.requires_approval:
            denied_reason = "approval_required"
            message = "Tool requires an explicit approval workflow and cannot be invoked through this endpoint"
        else:
            message = ""

        if denied_reason:
            with self._connect() as db:
                db.execute(
                    """UPDATE tool_executions SET status = 'denied',
                       error_code = ?, finished_at = ? WHERE id = ?""",
                    (denied_reason, datetime.now(timezone.utc).isoformat(), execution_id),
                )
            raise ToolError(message)

        try:
            parsed = spec.input_model.model_validate(arguments)
            result = spec.handler(parsed, context)
            if inspect.isawaitable(result):
                result = await result
            finished = datetime.now(timezone.utc).isoformat()
            summary = json.dumps(
                {"type": type(result).__name__, "items": len(result) if isinstance(result, (list, dict)) else None},
                ensure_ascii=False,
            )
            with self._connect() as db:
                db.execute(
                    """UPDATE tool_executions SET status = 'completed',
                       result_summary = ?, finished_at = ? WHERE id = ?""",
                    (summary, finished, execution_id),
                )
            return {"execution_id": execution_id, "tool_id": tool_id, "status": "completed", "result": result}
        except Exception as exc:
            finished = datetime.now(timezone.utc).isoformat()
            code = "validation_error" if exc.__class__.__name__ == "ValidationError" else "execution_error"
            with self._connect() as db:
                db.execute(
                    """UPDATE tool_executions SET status = 'failed',
                       error_code = ?, finished_at = ? WHERE id = ?""",
                    (code, finished, execution_id),
                )
            if code == "validation_error":
                raise ToolError("Tool arguments failed schema validation") from exc
            raise

    def audit(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                """SELECT id, tool_id, status, input_digest, result_summary,
                   error_code, started_at, finished_at FROM tool_executions
                   ORDER BY started_at DESC LIMIT ?""",
                (max(1, min(limit, 200)),),
            ).fetchall()
        return [dict(row) for row in rows]


def build_default_registry(database_path: Path) -> ToolRegistry:
    registry = ToolRegistry(database_path)
    registry.register(ToolSpec(
        id="memory.search",
        name="Search Memory",
        description="Search the currently configured memory index. Read-only.",
        risk="low",
        enabled=True,
        requires_approval=False,
        input_model=MemorySearchInput,
        handler=lambda args, ctx: ctx["memory"].search(args.query, limit=args.limit),
    ))
    registry.register(ToolSpec(
        id="automations.list",
        name="List Automations",
        description="List saved automation definitions. Read-only.",
        risk="low",
        enabled=True,
        requires_approval=False,
        input_model=EmptyToolInput,
        handler=lambda args, ctx: ctx["automations"].list(),
    ))
    registry.register(ToolSpec(
        id="integrations.status",
        name="Integration Status",
        description="Read current integration configuration and authorization metadata.",
        risk="low",
        enabled=True,
        requires_approval=False,
        input_model=EmptyToolInput,
        handler=lambda args, ctx: ctx["integrations"](),
    ))
    registry.register(ToolSpec(
        id="email.send",
        name="Send Email",
        description="Reserved for a provider-specific mail adapter and explicit user approval.",
        risk="high",
        enabled=False,
        requires_approval=True,
        input_model=EmptyToolInput,
    ))
    registry.register(ToolSpec(
        id="calendar.create_event",
        name="Create Calendar Event",
        description="Reserved for a provider-specific calendar adapter and explicit user approval.",
        risk="high",
        enabled=False,
        requires_approval=True,
        input_model=EmptyToolInput,
    ))
    registry.register(ToolSpec(
        id="system.admin",
        name="System Administration",
        description="Disabled until identity, role permissions and approval controls are complete.",
        risk="critical",
        enabled=False,
        requires_approval=True,
        input_model=EmptyToolInput,
    ))
    return registry
