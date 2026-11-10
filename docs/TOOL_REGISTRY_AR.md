# Tool Registry and Execution Audit

## Implemented safe tools
- `memory.search`: read-only search against the existing configured memory index.
- `automations.list`: read-only listing of saved automation definitions.
- `integrations.status`: read-only integration configuration metadata.

Each tool has a stable ID, description, risk level, enabled flag, approval requirement and Pydantic input schema.

## Disabled tools
- `email.send`
- `calendar.create_event`
- `system.admin`

These entries are catalog metadata only. They have no execution handler and cannot run through the tool endpoint. Email/calendar provider-specific API support, user identity, role authorization and explicit approval UI must exist before enabling write operations.

## API
- `GET /v1/tools`: returns allowlisted tool metadata and input schemas.
- `POST /v1/tools/{tool_id}/execute`: validates arguments and executes an enabled, non-approval read-only tool.
- `GET /v1/tools/audit`: returns recent execution metadata.

All routes require the backend bearer API key.

## Audit design
- Stores tool ID, status, timestamp, SHA-256 digest of arguments, a minimal result summary and a sanitized error code.
- Does not persist raw tool arguments or returned content in the audit table.
- Records denied calls to unknown, disabled or approval-gated tools.
- Does not yet include a per-user actor ID because the current backend uses one shared bearer key.

## Deliberate limits
- Tools are exposed through a deterministic API registry; the LLM does not automatically invoke tools through model function calling yet.
- The current safe tools are read-only and use the existing configured services only.
- No shell, arbitrary HTTP fetch, file write, email send, calendar write or public collection tool is enabled.
- Multi-user RBAC and tenant isolation remain prerequisites for broader tool enablement.
