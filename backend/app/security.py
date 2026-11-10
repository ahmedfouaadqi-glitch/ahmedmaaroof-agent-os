import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import get_settings

bearer = HTTPBearer(auto_error=False)

def require_api_key(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    settings = get_settings()
    if not settings.agent_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Backend authentication is not configured. Set AGENT_API_KEY.")
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    if not secrets.compare_digest(credentials.credentials, settings.agent_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return "authenticated"
