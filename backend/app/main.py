import asyncio
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from app.config import get_settings
from app.schemas import AgentRunRequest, AutomationIn, AutomationToggle, ChatRequest, ChatResponse, DocumentIn, SearchRequest, VoiceSpeakIn
from app.security import require_api_key
from app.services.automation import AutomationStore
from app.services.automation_worker import AutomationWorker
from app.services.voice import VoiceServices, VoiceServiceError
from app.services.oauth import OAuthConnector, OAuthError
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
    app.state.voice = VoiceServices(settings)
    app.state.oauth = OAuthConnector(settings.database_path, settings)
    app.state.automation_worker = None
    app.state.automation_worker_task = None
    if settings.automation_worker_enabled:
        app.state.automation_worker = AutomationWorker(
            app.state.automations, app.state.agent,
            poll_seconds=settings.automation_poll_seconds,
            timeout_seconds=settings.automation_timeout_seconds,
        )
        app.state.automation_worker_task = asyncio.create_task(
            app.state.automation_worker.run(), name="agent-os-automation-worker"
        )
    try:
        yield
    finally:
        if app.state.automation_worker:
            await app.state.automation_worker.stop()
        if app.state.automation_worker_task:
            try:
                await asyncio.wait_for(app.state.automation_worker_task, timeout=5)
            except asyncio.TimeoutError:
                app.state.automation_worker_task.cancel()
                try:
                    await app.state.automation_worker_task
                except asyncio.CancelledError:
                    pass

app = FastAPI(title="Ahmed Maaroof Agent OS API", version="0.2.0", description="Bilingual personal agent operating system API.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["GET","POST","PATCH","DELETE","OPTIONS"], allow_headers=["Authorization","Content-Type","apikey","x-client-info"])

@app.get("/v1/health", tags=["system"])
async def health():
    return {"status":"ok","service":"ahmed-maaroof-agent-os","version":"0.2.0","model_configured":bool(settings.openrouter_api_key),"auth_configured":bool(settings.agent_api_key),"automation_worker_enabled":settings.automation_worker_enabled}

@app.get("/v1/system/stats", dependencies=[Depends(require_api_key)], tags=["system"])
async def system_stats():
    return {"memory":app.state.memory.stats(),"retrieval_mode":app.state.memory.retrieval_mode,"model_configured":bool(settings.openrouter_api_key),"automation_count":len(app.state.automations.list()),"automation_worker_enabled":settings.automation_worker_enabled}

@app.get("/v1/integrations/status", dependencies=[Depends(require_api_key)], tags=["integrations"])
async def integrations():
    items = integration_status(settings)
    for item in items:
        if item["id"] in ("email", "calendar"):
            item["authorized"] = app.state.oauth.status(item["id"])["connected"]
    return {"integrations": items}

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



@app.post("/v1/oauth/{integration}/start", dependencies=[Depends(require_api_key)], tags=["integrations"])
async def oauth_start(integration: str):
    try:
        return app.state.oauth.create_authorization(integration)
    except OAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.get("/v1/oauth/{integration}/callback", tags=["integrations"])
async def oauth_callback(integration: str, code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        raise HTTPException(status_code=400, detail="OAuth provider denied authorization")
    if not code or not state:
        raise HTTPException(status_code=400, detail="OAuth code and state are required")
    try:
        return await app.state.oauth.complete_authorization(integration, code, state)
    except OAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/v1/oauth/{integration}/status", dependencies=[Depends(require_api_key)], tags=["integrations"])
async def oauth_status(integration: str):
    try:
        return app.state.oauth.status(integration)
    except OAuthError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@app.delete("/v1/oauth/{integration}", dependencies=[Depends(require_api_key)], tags=["integrations"])
async def oauth_disconnect(integration: str):
    try:
        return {"disconnected": app.state.oauth.disconnect(integration)}
    except OAuthError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@app.get("/v1/voice/status", dependencies=[Depends(require_api_key)], tags=["voice"])
async def voice_status():
    return await app.state.voice.status()

@app.post("/v1/voice/transcribe", dependencies=[Depends(require_api_key)], tags=["voice"])
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = Form(default=None, max_length=12),
):
    allowed = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/webm", "audio/ogg", "audio/mp4", "audio/aac", "application/octet-stream"}
    if file.content_type and file.content_type not in allowed:
        raise HTTPException(status_code=415, detail="Unsupported audio content type")
    audio = await file.read(15 * 1024 * 1024 + 1)
    if not audio:
        raise HTTPException(status_code=400, detail="Audio file is empty")
    if len(audio) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio file exceeds 15 MB")
    try:
        return await app.state.voice.transcribe(
            audio, file.filename or "recording", file.content_type or "application/octet-stream", language
        )
    except VoiceServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@app.post("/v1/voice/speak", dependencies=[Depends(require_api_key)], tags=["voice"])
async def speak_text(request: VoiceSpeakIn):
    try:
        audio, media_type = await app.state.voice.speak(
            request.input, request.voice, request.response_format
        )
        return Response(content=audio, media_type=media_type)
    except VoiceServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@app.get("/v1/automations", dependencies=[Depends(require_api_key)], tags=["automations"])
async def list_automations():
    return {"automations":app.state.automations.list(),"scheduler":"running" if settings.automation_worker_enabled else "disabled","worker_enabled":settings.automation_worker_enabled}

@app.post("/v1/automations", dependencies=[Depends(require_api_key)], tags=["automations"])
async def create_automation(request: AutomationIn):
    return app.state.automations.create(request.name,request.prompt,request.interval_minutes)

@app.patch("/v1/automations/{automation_id}", dependencies=[Depends(require_api_key)], tags=["automations"])
async def toggle_automation(automation_id: str, request: AutomationToggle):
    result=app.state.automations.set_enabled(automation_id,request.enabled)
    if not result:
        raise HTTPException(status_code=404,detail="Automation not found")
    return result

@app.get("/v1/automations/{automation_id}/executions", dependencies=[Depends(require_api_key)], tags=["automations"])
async def automation_executions(automation_id: str, limit: int = 20):
    if not app.state.automations.get(automation_id):
        raise HTTPException(status_code=404,detail="Automation not found")
    return {"executions":app.state.automations.executions(automation_id, max(1, min(limit, 100)))}

@app.delete("/v1/automations/{automation_id}", dependencies=[Depends(require_api_key)], tags=["automations"])
async def delete_automation(automation_id: str):
    if not app.state.automations.delete(automation_id):
        raise HTTPException(status_code=404,detail="Automation not found")
    return {"deleted":True}
