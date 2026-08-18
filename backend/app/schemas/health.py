from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    repository: str
    provider: str
