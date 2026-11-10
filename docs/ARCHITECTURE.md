# Ahmed Maaroof Agent OS — Architecture

## Layers
- **React / Vite UI:** bilingual Arabic/English workspace, RTL/LTR.
- **FastAPI:** authenticated API, orchestrator, model gateway, skills, automation definitions and integration status.
- **Orchestrator:** Plan → Retrieve → Route → Execute → Reflect. Explicit skill selection is supported; heuristic routing is only a default.
- **Memory adapter:** current SQLite FTS5 + Markdown Vault implementation. No new knowledge source is selected or ingested in this phase.
- **Model Gateway:** server-side OpenRouter adapter with fallback model list.
- **Skills:** allowlisted capabilities. High-risk administration and collection skills remain disabled.
- **Automation store:** persistent SQLite definitions. A scheduler/worker is not yet implemented.
- **Integration adapters:** configuration/status contracts for email, calendar, Whisper, Kokoro and design providers. Status does not imply live connectivity.
- **Vercel:** static frontend only. Persistent FastAPI, SQLite and local sidecars require a persistent host or local runtime.

## Request flow
1. Authenticate request.
2. Plan and select an allowlisted skill.
3. Retrieve indexed evidence.
4. Execute via configured model provider.
5. Return answer, model, usage, skill, execution stages and source citations.

## Security
- API routes fail closed without AGENT_API_KEY.
- Provider credentials stay server-side.
- Retrieved content is treated as untrusted evidence.
- High-risk skills are disabled.
- Do not place secrets in the Vault or frontend bundle.
- Production requires user-scoped auth, workspace isolation, rate limits, audit retention and OAuth token encryption.

## Deferred
- Selection and connection of knowledge sources.
- Real email/calendar OAuth and operations.
- Persistent automation scheduler/worker.
- Local voice service protocol and runtime.
- Image/video provider integration and approval workflow.
