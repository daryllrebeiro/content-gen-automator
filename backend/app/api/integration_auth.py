from fastapi import Header, HTTPException

from app.config import settings


def require_integration_auth(authorization: str | None = Header(default=None)) -> None:
    if settings.app_env == "development" and not settings.integration_service_token:
        return
    expected = f"Bearer {settings.integration_service_token}"
    if not settings.integration_service_token or authorization != expected:
        raise HTTPException(status_code=401, detail="Integration authentication required")

