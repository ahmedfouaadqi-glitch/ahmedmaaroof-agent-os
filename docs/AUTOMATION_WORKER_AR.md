# Automation Worker — Implementation and Operations

## Implemented
- SQLite-backed automation definitions with additive migration of scheduling metadata.
- Opt-in asynchronous worker started and stopped with the FastAPI lifespan.
- Atomic `BEGIN IMMEDIATE` due-job claims and expiring leases to reduce duplicate execution across worker processes.
- Persistent execution history with running/completed/failed states, bounded output/error fields and per-automation history endpoint.
- Configurable polling and execution timeout.
- Failure retry backoff (5, then 10 minutes); after the configured retry attempts, the next attempt is deferred to the automation interval.
- Enabling an automation schedules its first run after the selected interval; it does not run immediately.
- Worker is disabled by default. No scheduled model calls occur unless the operator explicitly enables it.

## Configuration
Set on the backend host only:
- `AUTOMATION_WORKER_ENABLED=true`
- `AUTOMATION_POLL_SECONDS=5`
- `AUTOMATION_TIMEOUT_SECONDS=120`

The worker calls the configured AgentOrchestrator, which may invoke the configured model provider. Enabling the worker can therefore incur provider charges. Keep it disabled until the provider, budget and prompts are reviewed.

## API
- `GET /v1/automations` reports worker readiness and definitions.
- `POST /v1/automations` creates a disabled definition.
- `PATCH /v1/automations/{id}` enables/disables and schedules/cancels it.
- `GET /v1/automations/{id}/executions` returns bounded execution history.
- `DELETE /v1/automations/{id}` deletes the definition.

All routes require the configured bearer API key.

## Operational limits
- This is an in-process worker. The backend must run as a persistent process; serverless request runtimes are not suitable.
- SQLite leases mitigate concurrent claims, but this is not a distributed queue. Use one persistent backend instance for production until a dedicated queue/worker deployment is designed.
- A process crash can leave an execution marked `running` until its lease expires. Recovery/reconciliation of stale execution records is a follow-up.
- There is no user/workspace ownership model yet; do not expose this API to multiple untrusted users.
- No external paid calls were triggered during implementation or verification.
