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

Copy `.env.example` to `.env`. Never expose OpenRouter or service-role keys in browser variables.

## Lovable integration
See [Lovable setup](docs/LOVABLE_SETUP_AR.md) and [the build prompt](docs/LOVABLE_PROMPT_AR.md). Lovable owns the UI workflow; FastAPI remains the trusted execution and memory layer.

## Status
Foundation 0.1. Backend unit tests: **4 passed** in the authoring environment. Frontend production build, live provider credentials, Supabase deployment, FAISS activation and Vercel deployment require separate setup and verification.

See [execution status](docs/EXECUTION_STATUS_AR.md), [architecture](docs/ARCHITECTURE.md) and [roadmap](docs/ROADMAP_AR.md).
