# Ahmed Maaroof Agent OS

Bilingual personal Agent OS foundation (Arabic/English, RTL/LTR) designed to work with Lovable as the UI builder while keeping secrets and agent execution on trusted server-side services.

## Architecture
- **Web UI:** React 19, Vite, TypeScript, Tailwind CSS.
- **API:** Python 3.12, FastAPI.
- **Memory:** Markdown Vault (Obsidian-compatible) plus SQLite FTS5 search.
- **Optional semantic retrieval:** FAISS adapter, installed separately.
- **Model gateway:** OpenRouter adapter; API keys remain server-side.
- **Lovable:** Builds/maintains the frontend and connects to the secured API gateway.
- **Deployment:** Vercel frontend; FastAPI on a separately managed server. Supabase Edge Function is an optional authenticated gateway.

## Repository layout
```
backend/                 FastAPI, memory services, skills, tests, Markdown Vault
src/                     React application
supabase/                Optional Edge Function and SQL migration
docs/                    Architecture, roadmap and Lovable setup
.github/workflows/       CI
```

## Quick start

### API
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest -q
```

### Frontend
```bash
npm install
npm run dev
```

### Persistent backend container
```bash
cp .env.example .env
chmod 600 .env
# Set AGENT_API_KEY and trusted provider settings in .env before starting.
docker compose config
docker compose up -d --build
docker compose ps
```

The backend binds to `127.0.0.1:8000` by default. Put a TLS reverse proxy in front of it; do not expose the API port directly. See [deployment preparation](docs/DEPLOYMENT_PREPARATION_AR.md).

Copy `.env.example` to `.env`. Never expose OpenRouter or service-role keys in browser variables.

## Lovable integration
See [Lovable setup](docs/LOVABLE_SETUP_AR.md) and [the build prompt](docs/LOVABLE_PROMPT_AR.md). Lovable owns the UI workflow; FastAPI remains the trusted execution and memory layer.

## Status
The repository now contains a nine-section workspace UI, FastAPI services for memory/automation/voice/OAuth/Designer, an allowlisted tool registry, baseline API hardening and integration tests. CI verification is tracked in the open pull requests. Real provider credentials, local voice sidecars, OAuth tenant consent, user/workspace isolation, browser E2E, production secrets and live deployment still require separate verification. This is a personal single-owner foundation and is not yet production-ready for multiple untrusted users.

See [execution status](docs/EXECUTION_STATUS_AR.md), [architecture](docs/ARCHITECTURE.md) and [roadmap](docs/ROADMAP_AR.md).
