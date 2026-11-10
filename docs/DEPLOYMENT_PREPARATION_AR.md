# Deployment Preparation — FastAPI Backend and Vercel Frontend

## Prepared deployment artifacts
- `backend/Dockerfile`: Python 3.12 image, non-root runtime user, persistent data directory and exactly one Uvicorn worker.
- `docker-compose.yml`: persistent SQLite/designer volume, read-only Vault mount, localhost-only port binding by default, health check, read-only container filesystem, dropped Linux capabilities and no-new-privileges.
- `vercel.json`: existing Vite static frontend configuration.

## Backend setup
1. Copy `.env.example` to `.env`.
2. Generate a long random `AGENT_API_KEY` and set it only in the backend environment.
3. Set `CORS_ORIGINS` to the exact frontend origin.
4. Keep `AUTOMATION_WORKER_ENABLED=false` until model cost, persistent uptime and automation prompts have been reviewed.
5. Keep Designer cost settings at zero until provider pricing and a spending limit have been verified.
6. Configure OAuth only after the provider, client credentials, callback URLs and least-privilege scopes are selected.
7. Restrict the environment file: `chmod 600 .env`. Never commit it.

Start the backend:
```bash
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs -f api
```

The API port binds to `127.0.0.1:8000` by default. Place a TLS reverse proxy in front of it; do not expose port 8000 directly to the public internet. Set `API_BIND_ADDRESS=0.0.0.0` only when a separately controlled network boundary requires it.

## Frontend on Vercel
- Import the repository and deploy the Vite project using the existing `vercel.json`.
- Set `VITE_AGENT_API_URL` to the HTTPS backend origin in Vercel environment variables.
- Do not place API keys, OAuth secrets, OpenRouter keys or Designer provider keys in any `VITE_*` variable.
- Add the exact Vercel production and preview origins to backend `CORS_ORIGINS` only when needed.

## Runtime constraints
- Keep one Uvicorn worker: the current automation worker is in-process.
- SQLite and Designer artifacts are stored in the named `agent_data` volume. Back up this volume and test restoration before production.
- `docker compose down` preserves the named volume. Do not use `docker compose down -v` unless data deletion is intended.
- The container health check only verifies the FastAPI health endpoint; it does not prove model, OAuth, voice, Designer or mail/calendar provider availability.

## Not deployed / not production-ready
No VPS, DNS, TLS certificate, Vercel project binding or production credentials were supplied. No deployment has been executed. The backend still uses one shared bearer API key and does not yet provide user accounts, RBAC or workspace isolation. Do not expose this deployment publicly or use it for multiple untrusted users until those controls and a security review are complete.
