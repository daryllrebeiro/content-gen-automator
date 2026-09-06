import hmac
from uuid import UUID
from fastapi import Header, HTTPException

from app.domain.project import Project
from app.services.project_service import ProjectNotFoundError, ProjectService

project_service = ProjectService()


def require_project_owner(
    project_id: UUID,
    x_project_owner_token: str | None = Header(default=None, alias="X-Project-Owner-Token"),
) -> Project:
    """
    Enforces per-project tenant ownership authorization.
    Validates the caller's X-Project-Owner-Token against the high-entropy server-side token.
    Uses constant-time comparison (hmac.compare_digest) to prevent timing attacks.
    """
    try:
        project = project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    stored_token = getattr(project, "owner_token", None) or ""
    if not stored_token or not x_project_owner_token or not hmac.compare_digest(x_project_owner_token, stored_token):
        raise HTTPException(
            status_code=403,
            detail="Access denied: Valid X-Project-Owner-Token required for this project."
        )
    return project
