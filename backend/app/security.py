from functools import lru_cache
import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.services.rate_limiter import SQLiteRateLimiter

bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=4)
def _rate_limiter(database_path: str) -> SQLiteRateLimiter:
    from pathlib import Path
    return SQLiteRateLimiter(Path(database_path))


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    settings = get_settings()
    if not settings.agent_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Backend authentication is not configured. Set AGENT_API_KEY.")
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    if not secrets.compare_digest(credentials.credentials, settings.agent_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    limiter = _rate_limiter(str(settings.database_path))
    allowed, retry_after = limiter.consume(
        "api:" + _client_ip(request) + ":" + credentials.credentials,
        settings.rate_limit_per_minute,
        settings.rate_limit_window_seconds,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
    return "authenticated"


def require_public_rate_limit(request: Request) -> None:
    settings = get_settings()
    limiter = _rate_limiter(str(settings.database_path))
    allowed, retry_after = limiter.consume(
        "public:" + _client_ip(request),
        settings.public_rate_limit_per_minute,
        settings.rate_limit_window_seconds,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Public endpoint rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
