from uuid import UUID
import hashlib
import json

from fastapi import APIRouter, Depends, Header, HTTPException

from app.schemas.health import HealthResponse, ReadinessResponse
from app.config import settings
from app.schemas.projects import (
    FactResponse,
    ExportResponse,
    ProjectCreateRequest,
    ProjectResponse,
    PromptResponse,
    PublishingResponse,
    SceneResponse,
    IntegrationProjectResponse,
    IntegrationPromptResponse,
    IntegrationStatusResponse,
    ApprovalRequest,
    ApprovalResponse,
)
from app.domain.project import ProjectInput
from app.services.project_service import (
    ProjectNotFoundError,
    ProjectService,
    ProjectStateError,
)
from app.services.export_service import ExportService
from app.api.integration_auth import require_integration_auth


router = APIRouter()
project_service = ProjectService()
export_service = ExportService()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="shorts-prompt-agent", environment=settings.app_env)


@router.get("/ready", response_model=ReadinessResponse, tags=["system"])
def readiness() -> ReadinessResponse:
    repository = project_service.repository
    if hasattr(repository, "engine"):
        from sqlalchemy import text

        with repository.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    return ReadinessResponse(status="ready", repository=settings.project_repository, provider=settings.llm_provider)


def _prompt_response(prompt) -> PromptResponse:
    return PromptResponse(
        scene_number=prompt.scene_number,
        total_scenes=prompt.total_scenes,
        text=prompt.text,
        narration=prompt.narration,
        narration_word_count=prompt.narration_word_count,
        estimated_narration_seconds=prompt.estimated_narration_seconds,
        version_number=prompt.version_number,
        template_version=prompt.template_version,
        why_this_prompt=prompt.why_this_prompt,
        quality_scores=prompt.quality_scores,
        provider_name=prompt.provider_name,
        model_name=prompt.model_name,
        generation_latency_ms=prompt.generation_latency_ms,
        repair_attempts=prompt.repair_attempts,
        estimated_input_tokens=prompt.estimated_input_tokens,
        estimated_output_tokens=prompt.estimated_output_tokens,
    )


def _project_response(project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        status=project.status.value,
        topic=project.input.topic,
        duration_seconds=project.input.duration_seconds,
        current_scene_number=project.current_scene_number,
        total_scenes=len(project.scenes),
        story_hook=project.story_hook,
        story_central_claim=project.story_central_claim,
        story_ending=project.story_ending,
        facts=[
            FactResponse(
                id=fact.id,
                text=fact.text,
                status=fact.status.value,
                confidence=fact.confidence,
                sources=fact.sources,
                notes=fact.notes,
                approved_for_narration=fact.approved_for_narration,
            )
            for fact in project.facts
        ],
        scenes=[SceneResponse(**scene.__dict__) for scene in project.scenes],
        continuity=project.continuity.__dict__,
        prompts=[_prompt_response(prompt) for prompt in project.prompts.values()],
    )


@router.post("/api/projects", response_model=ProjectResponse, tags=["projects"])
def create_project(request: ProjectCreateRequest) -> ProjectResponse:
    project = project_service.create(
        ProjectInput(
            topic=request.topic,
            facts=request.facts,
            source_urls=request.source_urls,
            language=request.language,
            tone=request.tone,
            audience=request.audience,
            visual_preferences=request.visual_preferences,
            duration_seconds=request.duration_seconds,
        )
    )
    return _project_response(project)


@router.get("/api/projects/{project_id}", response_model=ProjectResponse, tags=["projects"])
def get_project(project_id: UUID) -> ProjectResponse:
    try:
        return _project_response(project_service.repository.get(project_id))
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/generate",
    response_model=PromptResponse,
    tags=["prompts"],
)
def generate_first_prompt(project_id: UUID) -> PromptResponse:
    try:
        return _prompt_response(project_service.generate_next(project_id))
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/api/projects/{project_id}/prompts/next",
    response_model=PromptResponse,
    tags=["prompts"],
)
def generate_next_prompt(project_id: UUID) -> PromptResponse:
    return generate_first_prompt(project_id)


@router.post(
    "/api/projects/{project_id}/prompts/{scene_number}/regenerate",
    response_model=PromptResponse,
    tags=["prompts"],
)
def regenerate_prompt(project_id: UUID, scene_number: int) -> PromptResponse:
    try:
        return _prompt_response(project_service.regenerate(project_id, scene_number))
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/api/projects/{project_id}/export",
    response_model=ExportResponse,
    tags=["export"],
)
def export_project(project_id: UUID) -> ExportResponse:
    try:
        project = project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    publishing = export_service.publishing_package(project)
    return ExportResponse(
        project_id=project.id,
        markdown=export_service.render_markdown(project),
        publishing=PublishingResponse(**publishing.__dict__),
        data=export_service.export_json(project),
    )


@router.post(
    "/api/integrations/projects",
    response_model=IntegrationProjectResponse,
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_create_project(
    request: ProjectCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> IntegrationProjectResponse:
    payload = request.model_dump(mode="json")
    request_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    try:
        project, existed = project_service.create_idempotent(
            idempotency_key,
            request_hash,
            ProjectInput(
                topic=request.topic,
                facts=request.facts,
                source_urls=request.source_urls,
                language=request.language,
                tone=request.tone,
                audience=request.audience,
                visual_preferences=request.visual_preferences,
                duration_seconds=request.duration_seconds,
            ),
        )
    except ProjectStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if request_id:
        project_service._audit("integration.project_create", str(project.id), request_id, {"idempotency_key": idempotency_key, "replayed": existed})
    return IntegrationProjectResponse(project_id=project.id, created=not existed, status=project.status.value, total_scenes=len(project.scenes))


@router.get(
    "/api/integrations/projects/{project_id}/status",
    response_model=IntegrationStatusResponse,
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_project_status(project_id: UUID, request_id: str | None = Header(default=None, alias="X-Request-ID")) -> IntegrationStatusResponse:
    try:
        project = project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    if request_id:
        project_service._audit("integration.project_status", str(project.id), request_id)
    next_scene = project.current_scene_number + 1 if project.current_scene_number < len(project.scenes) else None
    return IntegrationStatusResponse(
        project_id=project.id,
        status=project.status.value,
        current_scene_number=project.current_scene_number,
        total_scenes=len(project.scenes),
        next_scene_number=next_scene,
    )


@router.post(
    "/api/integrations/projects/{project_id}/prompts/next",
    response_model=IntegrationPromptResponse,
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_generate_next_prompt(
    project_id: UUID,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> IntegrationPromptResponse:
    request_hash = hashlib.sha256(f"integration.prompts.next:{project_id}".encode()).hexdigest()
    existing = getattr(project_service.repository, "get_idempotency", lambda _: None)(idempotency_key)
    if existing is not None and (existing.operation != "integration.prompts.next" or existing.request_hash != request_hash):
        raise HTTPException(status_code=409, detail="Idempotency key was reused with a different request.")
    try:
        prompt = project_service.generate_next(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if existing is None and hasattr(project_service.repository, "save_idempotency"):
        from app.domain.integration import IdempotencyRecord
        from datetime import datetime, timezone
        project_service.repository.save_idempotency(IdempotencyRecord(idempotency_key, "integration.prompts.next", request_hash, {"project_id": str(project_id), "scene_number": prompt.scene_number}, datetime.now(timezone.utc)))
    if request_id:
        project_service._audit("integration.prompt_next", str(project_id), request_id, {"scene_number": prompt.scene_number, "idempotency_key": idempotency_key})
    project = project_service.repository.get(project_id)
    return IntegrationPromptResponse(project_id=project.id, prompt=_prompt_response(prompt), status=project.status.value)


@router.get(
    "/api/integrations/projects/{project_id}/export",
    response_model=ExportResponse,
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_export_project(project_id: UUID, request_id: str | None = Header(default=None, alias="X-Request-ID")) -> ExportResponse:
    result = export_project(project_id)
    if request_id:
        project_service._audit("integration.project_export", str(project_id), request_id)
    return result


def _integration_decide_prompt(project_id: UUID, scene_number: int, decision: str, request: ApprovalRequest, idempotency_key: str, request_id: str | None) -> ApprovalResponse:
    request_hash = hashlib.sha256(json.dumps({"project_id": str(project_id), "scene_number": scene_number, "decision": decision, **request.model_dump()}, sort_keys=True).encode()).hexdigest()
    existing = getattr(project_service.repository, "get_idempotency", lambda _: None)(idempotency_key)
    operation = f"integration.prompts.{decision}"
    if existing is not None and (existing.operation != operation or existing.request_hash != request_hash):
        raise HTTPException(status_code=409, detail="Idempotency key was reused with a different request.")
    try:
        project = project_service.decide_prompt(project_id, scene_number, decision=decision, actor=request.actor, comment=request.comment)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if existing is None and hasattr(project_service.repository, "save_idempotency"):
        from app.domain.integration import IdempotencyRecord
        from datetime import datetime, timezone
        project_service.repository.save_idempotency(IdempotencyRecord(idempotency_key, operation, request_hash, {"project_id": str(project_id), "scene_number": scene_number, "decision": decision}, datetime.now(timezone.utc)))
    if request_id:
        project_service._audit(f"integration.prompt_{decision}", str(project_id), request_id, {"scene_number": scene_number, "actor": request.actor})
    return ApprovalResponse(project_id=project.id, scene_number=scene_number, decision=decision, status=project.status.value)


@router.post(
    "/api/integrations/projects/{project_id}/prompts/{scene_number}/approve",
    response_model=ApprovalResponse,
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_approve_prompt(project_id: UUID, scene_number: int, request: ApprovalRequest, idempotency_key: str = Header(alias="Idempotency-Key"), request_id: str | None = Header(default=None, alias="X-Request-ID")) -> ApprovalResponse:
    return _integration_decide_prompt(project_id, scene_number, "approved", request, idempotency_key, request_id)


@router.post(
    "/api/integrations/projects/{project_id}/prompts/{scene_number}/reject",
    response_model=ApprovalResponse,
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_reject_prompt(project_id: UUID, scene_number: int, request: ApprovalRequest, idempotency_key: str = Header(alias="Idempotency-Key"), request_id: str | None = Header(default=None, alias="X-Request-ID")) -> ApprovalResponse:
    return _integration_decide_prompt(project_id, scene_number, "rejected", request, idempotency_key, request_id)
