from typing import Literal
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    language: Literal["ar", "en"] | None = None

class AgentRunRequest(ChatRequest):
    skill_id: str | None = Field(default=None, max_length=100)

class SourceItem(BaseModel):
    id: str
    title: str
    source: str
    excerpt: str
    score: float | None = None

class ChatResponse(BaseModel):
    answer: str
    model: str
    sources: list[SourceItem] = []
    usage: dict[str, int] | None = None

class DocumentIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=500_000)
    source: str = Field(default="manual", max_length=500)

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    limit: int = Field(default=6, ge=1, le=20)

class AutomationIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    prompt: str = Field(min_length=5, max_length=4_000)
    interval_minutes: int = Field(ge=15, le=43_200)

class AutomationToggle(BaseModel):
    enabled: bool

class VoiceSpeakIn(BaseModel):
    input: str = Field(min_length=1, max_length=12_000)
    voice: str = Field(default="af_heart", min_length=1, max_length=80)
    response_format: Literal["mp3", "wav", "opus", "aac", "flac"] = "mp3"
