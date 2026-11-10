from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    agent_api_key: str = ""
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    vault_path: Path = Path("./Vault")
    database_path: Path = Path("./data/agent_os.sqlite3")
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4.1-mini"
    openrouter_fallback_models: str = ""
    openrouter_site_url: str = "http://localhost:5173"
    openrouter_app_name: str = "Ahmed Maaroof Agent OS"
    enable_faiss: bool = False
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    oauth_token_encryption_key: str = ""
    email_oauth_authorization_url: str = ""
    email_oauth_token_url: str = ""
    email_oauth_client_id: str = ""
    email_oauth_client_secret: str = ""
    email_oauth_redirect_uri: str = ""
    email_oauth_scopes: str = ""
    calendar_oauth_authorization_url: str = ""
    calendar_oauth_token_url: str = ""
    calendar_oauth_client_id: str = ""
    calendar_oauth_client_secret: str = ""
    calendar_oauth_redirect_uri: str = ""
    calendar_oauth_scopes: str = ""
    email_provider_url: str = ""
    email_provider_token: str = ""
    calendar_provider_url: str = ""
    calendar_provider_token: str = ""
    whisper_service_url: str = ""
    kokoro_service_url: str = ""
    image_provider_api_key: str = ""
    designer_provider_endpoint: str = ""
    designer_provider_model: str = ""
    designer_cost_per_image_usd: float = Field(default=0, ge=0, le=100)
    designer_max_cost_usd: float = Field(default=0, ge=0, le=1000)
    designer_output_dir: Path = Path("./data/designer")
    automation_worker_enabled: bool = False
    automation_poll_seconds: int = Field(default=5, ge=1, le=300)
    automation_timeout_seconds: int = Field(default=120, ge=10, le=900)
    max_request_chars: int = Field(default=20_000, ge=1_000, le=100_000)

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def fallback_models(self) -> list[str]:
        return [model.strip() for model in self.openrouter_fallback_models.split(",") if model.strip()]

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
