from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.schemas import AgentRunRequest, AutomationIn, AutomationToggle, ChatRequest, ChatResponse, DocumentIn, SearchRequest
from app.security import require_api_key
from app.services.automation import AutomationStore
from app.services.agent import AgentOrchestrator
from app.services.integrations import integration_status
from app.services.memory import MemoryStore
from app.services.openrouter import OpenRouterProvider
from app.skills import list_skills

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.memory = MemoryStore(settings.database_path, vector_enabled=settings.enable_faiss, embedding_model=settings.embedding_model, vector_path=settings.database_path.parent / "faiss")
    app.state.provider = OpenRouterProvider(settings)
    app.state.agent = AgentOrchestrator(app.state.memory, app.state.provider)
    app.state.automations = AutomationStore(settings.database_path)
    yield

app = FastAPI(title="Ahmed Maaroof Agent OS API", version="0.2.0", description="Bilingual personal agent operating system API.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["GET","POST","PATCH","DELETE","OPTIONS"], allow_headers=["Authorization","Content-Type","apikey","x-client-info"])

@app.get("/v1/health", tags=["system"])
async def health():
    return {"status":"ok","service":"ahmed-maaroof-agent-os","version":"0.2.0","model_configured":bool(settings.openrouter_api_key),"auth_configured":bool(settings.agent_api_key)}

@app.get("/v1/system/stats", dependencies=[Depends(require_api_key)], tags=["system"])
async def system_stats():
    return {"memory":app.state.memory.stats(),"retrieval_mode":app.state.memory.retrieval_mode,"model_configured":bool(settings.openrouter_api_key),"automation_count":len(app.state.automations.list())}

@app.get("/v1/integrations/status", dependencies=[Depends(require_api_key)], tags=["integrations"])
async def integrations():
    return {"integrations":integration_status(settings)}

@app.get("/v1/skills", dependencies=[Depends(require_api_key)], tags=["skills"])
async def skills():
    return {"skills":list_skills()}

@app.post("/v1/memory/documents", dependencies=[Depends(require_api_key)], tags=["memory"])
async def add_document(document: DocumentIn):
    if len(document.content) > settings.max_request_chars * 25:
        raise HTTPException(status_code=413, detail="Document is too large")
    return app.state.memory.upsert_document(document.title, document.content, document.source)

@app.post("/v1/memory/ingest-vault", dependencies=[Depends(require_api_key)], tags=["memory"])
async def ingest_vault():
    return app.state.memory.ingest_vault(settings.vault_path)

@app.post("/v1/memory/search", dependencies=[Depends(require_api_key)], tags=["memory"])
async def search_memory(request: SearchRequest):
    return {"results":app.state.memory.search(request.query, request.limit)}

@app.post("/v1/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)], tags=["agent"])
async def chat(request: ChatRequest):
    if len(request.message) > settings.max_request_chars:
        raise HTTPException(status_code=413, detail="Message is too large")
    result = await app.state.agent.run(request.message, request.language)
    return ChatResponse(answer=result["answer"],model=result["model"],usage=result.get("usage"),sources=result["sources"])

@app.post("/v1/agent/run", dependencies=[Depends(require_api_key)], tags=["agent"])
async def run_agent(request: AgentRunRequest):
    if len(request.message) > settings.max_request_chars:
        raise HTTPException(status_code=413, detail="Message is too large")
    try:
        return await app.state.agent.run(request.message, request.language, request.skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/v1/automations", dependencies=[Depends(require_api_key)], tags=["automations"])
async def list_automations():
    return {"automations":app.state.automations.list(),"scheduler":"definitions-only"}

@app.post("/v1/automations", dependencies=[Depends(require_api_key)], tags=["automations"])
async def create_automation(request: AutomationIn):
    return app.state.automations.create(request.name,request.prompt,request.interval_minutes)

@app.patch("/v1/automations/{automation_id}", dependencies=[Depends(require_api_key)], tags=["automations"])
async def toggle_automation(automation_id: str, request: AutomationToggle):
    result=app.state.automations.set_enabled(automation_id,request.enabled)
    if not result:
        raise HTTPException(status_code=404,detail="Automation not found")
    return result

@app.delete("/v1/automations/{automation_id}", dependencies=[Depends(require_api_key)], tags=["automations"])
async def delete_automation(automation_id: str):
    if not app.state.automations.delete(automation_id):
        raise HTTPException(status_code=404,detail="Automation not found")
    return {"deleted":True}
