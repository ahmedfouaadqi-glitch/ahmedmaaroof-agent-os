# Ahmed Maaroof Agent OS — Architecture

## System boundaries
- **Lovable / React UI:** presentation, user interaction, Arabic/English and RTL/LTR.
- **FastAPI:** authenticated API, orchestration entry point, model gateway and memory access.
- **Markdown Vault:** human-readable project knowledge, compatible with Obsidian.
- **SQLite FTS5:** local lexical retrieval. The optional FAISS implementation is a later enhancement and is not enabled by default.
- **OpenRouter:** server-side model provider. The API key must never be shipped to the browser.
- **Supabase:** optional identity, workspace persistence and Edge Function gateway. It is not required for local API operation.
- **Vercel:** static frontend deployment. It does not host the persistent local Markdown Vault or FastAPI process.

## Request flow
1. The UI sends a message to FastAPI with a bearer token.
2. FastAPI validates the token and searches the local memory index.
3. Relevant excerpts are attached to the model prompt as untrusted evidence.
4. FastAPI calls OpenRouter using server-side credentials.
5. The response, model name, usage and retrieved sources are returned to the UI.

## Security controls
- Protected routes fail closed when `AGENT_API_KEY` is not configured.
- CORS origins are explicitly configured.
- API and provider secrets stay server-side.
- High-risk skills (network administration and collection) are disabled in the foundation and require separate implementation and approval.
- Never store passwords, API keys, private keys or router credentials in Markdown Vault notes.

## Lovable integration
Use Lovable to create or maintain the frontend, then configure its API URL and bearer-token flow against a secured backend. For production, prefer a user-scoped Supabase Edge gateway rather than embedding a shared backend token in browser code. See `LOVABLE_SETUP_AR.md`.

## Deployment topology
The Vite frontend can be deployed to Vercel. FastAPI and its Vault/database need a persistent host or remain local. A tunnel is optional and must be protected by authentication and restrictive network policy.
