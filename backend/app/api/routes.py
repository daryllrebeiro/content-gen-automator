from fastapi import APIRouter

from app.schemas.health import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="shorts-prompt-agent")

