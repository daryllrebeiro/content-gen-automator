import hmac
from fastapi import Header, HTTPException, status

from app.config import settings


def require_integration_auth(authorization: str | None = Header(default=None)) -> None:
    """Enforces authentication for internal integration and admin services.
    
    Fails closed: requires INTEGRATION_SERVICE_TOKEN to be configured and caller
    to provide a matching Bearer token in constant-time comparison.
    """
    if not settings.integration_service_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Integration service token is not configured on the server.",
        )
    expected = f"Bearer {settings.integration_service_token}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Integration authentication required",
        )


