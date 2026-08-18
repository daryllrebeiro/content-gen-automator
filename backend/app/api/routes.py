from uuid import UUID, uuid4
import hashlib
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query

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
    FactVerificationResponse,
    DeliveryJobResponse,
    ExportManifestResponse,
    ProductionJobResponse,
)
from app.domain.project import ProjectInput
from app.services.project_service import (
    ProjectNotFoundError,
    ProjectService,
    ProjectStateError,
)
from app.services.export_service import ExportService
from app.api.integration_auth import require_integration_auth
from app.services.delivery_service import DeliveryService
from app.services.production_service import ProductionService


router = APIRouter()
project_service = ProjectService()
export_service = ExportService()
delivery_service = DeliveryService()
production_service = ProductionService()


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


def _fact_job_response(job) -> FactVerificationResponse:
    return FactVerificationResponse(job_id=job.job_id, project_id=UUID(job.project_id), status=job.status, claim_count=job.claim_count, verified_count=job.verified_count, failed_count=job.failed_count, error=job.error)


@router.post(
    "/api/integrations/projects/{project_id}/facts/verify",
    response_model=FactVerificationResponse,
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_verify_facts(project_id: UUID, idempotency_key: str = Header(alias="Idempotency-Key"), request_id: str | None = Header(default=None, alias="X-Request-ID")) -> FactVerificationResponse:
    request_hash = hashlib.sha256(f"integration.facts.verify:{project_id}".encode()).hexdigest()
    existing = getattr(project_service.repository, "get_idempotency", lambda _: None)(idempotency_key)
    if existing is not None and (existing.operation != "integration.facts.verify" or existing.request_hash != request_hash):
        raise HTTPException(status_code=409, detail="Idempotency key was reused with a different request.")
    job_id = existing.response["job_id"] if existing is not None else str(uuid4())
    try:
        job = project_service.repository.get_fact_job(job_id) if existing is not None and hasattr(project_service.repository, "get_fact_job") else None
        if job is None:
            job = project_service.verify_facts(project_id, job_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    if existing is None and hasattr(project_service.repository, "save_idempotency"):
        from app.domain.integration import IdempotencyRecord
        from datetime import datetime, timezone
        project_service.repository.save_idempotency(IdempotencyRecord(idempotency_key, "integration.facts.verify", request_hash, {"job_id": job.job_id}, datetime.now(timezone.utc)))
    if request_id:
        project_service._audit("integration.facts_verify", str(project_id), request_id, {"job_id": job.job_id})
    return _fact_job_response(job)


@router.get(
    "/api/integrations/fact-verification-jobs/{job_id}",
    response_model=FactVerificationResponse,
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_fact_job_status(job_id: str) -> FactVerificationResponse:
    job = getattr(project_service.repository, "get_fact_job", lambda _: None)(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Fact verification job not found")
    return _fact_job_response(job)


def _manifest_response(manifest) -> ExportManifestResponse:
    return ExportManifestResponse(manifest_id=manifest.manifest_id, project_id=UUID(manifest.project_id), package_version=manifest.package_version, checksum=manifest.checksum, expires_at=manifest.expires_at.isoformat(), download_token=delivery_service.sign_manifest(manifest, settings.export_signing_secret))


@router.post(
    "/api/integrations/projects/{project_id}/exports/manifest",
    response_model=ExportManifestResponse,
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_create_export_manifest(project_id: UUID, idempotency_key: str = Header(alias="Idempotency-Key"), request_id: str | None = Header(default=None, alias="X-Request-ID")) -> ExportManifestResponse:
    request_hash = hashlib.sha256(f"integration.exports.manifest:{project_id}".encode()).hexdigest()
    existing = getattr(project_service.repository, "get_idempotency", lambda _: None)(idempotency_key)
    if existing is not None and (existing.operation != "integration.exports.manifest" or existing.request_hash != request_hash):
        raise HTTPException(status_code=409, detail="Idempotency key was reused with a different request.")
    try:
        manifest = project_service.repository.get_export_manifest(existing.response["manifest_id"]) if existing is not None and hasattr(project_service.repository, "get_export_manifest") else None
        if manifest is None:
            project = project_service.repository.get(project_id)
            manifest = delivery_service.create_manifest(project, project_service.repository, export_service)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    if existing is None and hasattr(project_service.repository, "save_idempotency"):
        from app.domain.integration import IdempotencyRecord
        from datetime import datetime, timezone
        project_service.repository.save_idempotency(IdempotencyRecord(idempotency_key, "integration.exports.manifest", request_hash, {"manifest_id": manifest.manifest_id}, datetime.now(timezone.utc)))
    if request_id:
        project_service._audit("integration.export_manifest", str(project_id), request_id, {"manifest_id": manifest.manifest_id, "checksum": manifest.checksum})
    return _manifest_response(manifest)


@router.get(
    "/api/integrations/exports/{manifest_id}/download",
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_download_export(manifest_id: str, token: str = Query(...)) -> dict:
    if delivery_service.verify_token(token, settings.export_signing_secret) != manifest_id:
        raise HTTPException(status_code=403, detail="Invalid or expired download token")
    manifest = getattr(project_service.repository, "get_export_manifest", lambda _: None)(manifest_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Export manifest not found")
    return {"manifest_id": manifest.manifest_id, "checksum": manifest.checksum, "package_version": manifest.package_version, "markdown": manifest.markdown, "data": manifest.data}


@router.post(
    "/api/integrations/projects/{project_id}/delivery",
    response_model=DeliveryJobResponse,
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_queue_delivery(project_id: UUID, manifest_id: str, idempotency_key: str = Header(alias="Idempotency-Key"), request_id: str | None = Header(default=None, alias="X-Request-ID")) -> DeliveryJobResponse:
    request_hash = hashlib.sha256(f"integration.delivery:{project_id}:{manifest_id}".encode()).hexdigest()
    existing = getattr(project_service.repository, "get_idempotency", lambda _: None)(idempotency_key)
    if existing is not None and (existing.operation != "integration.delivery" or existing.request_hash != request_hash):
        raise HTTPException(status_code=409, detail="Idempotency key was reused with a different request.")
    manifest = getattr(project_service.repository, "get_export_manifest", lambda _: None)(manifest_id)
    if manifest is None or manifest.project_id != str(project_id):
        raise HTTPException(status_code=404, detail="Export manifest not found")
    job = getattr(project_service.repository, "get_delivery_job", lambda _: None)(existing.response["job_id"]) if existing is not None else None
    if job is None:
        project = project_service.repository.get(project_id)
        job = delivery_service.queue_delivery(project, manifest, project_service.repository)
    if existing is None and hasattr(project_service.repository, "save_idempotency"):
        from app.domain.integration import IdempotencyRecord
        from datetime import datetime, timezone
        project_service.repository.save_idempotency(IdempotencyRecord(idempotency_key, "integration.delivery", request_hash, {"job_id": job.job_id}, datetime.now(timezone.utc)))
    return DeliveryJobResponse(job_id=job.job_id, project_id=project_id, manifest_id=job.manifest_id, status=job.status, attempts=job.attempts, error=job.error)


def _production_response(job) -> ProductionJobResponse:
    return ProductionJobResponse(job_id=job.job_id, project_id=UUID(job.project_id), scene_number=job.scene_number, prompt_version=job.prompt_version, job_type=job.job_type, provider=job.provider, provider_job_id=job.provider_job_id, status=job.status, contract=job.contract, artifact_id=job.artifact_id, error=job.error)


@router.post(
    "/api/integrations/projects/{project_id}/scenes/{scene_number}/production",
    response_model=ProductionJobResponse,
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_submit_production(project_id: UUID, scene_number: int, idempotency_key: str = Header(alias="Idempotency-Key"), request_id: str | None = Header(default=None, alias="X-Request-ID")) -> ProductionJobResponse:
    request_hash = hashlib.sha256(f"integration.production:{project_id}:{scene_number}".encode()).hexdigest()
    existing = getattr(project_service.repository, "get_idempotency", lambda _: None)(idempotency_key)
    if existing is not None and (existing.operation != "integration.production" or existing.request_hash != request_hash):
        raise HTTPException(status_code=409, detail="Idempotency key was reused with a different request.")
    try:
        project = project_service.repository.get(project_id)
        if project.status not in {project.status.APPROVED, project.status.COMPLETED}:
            raise ProjectStateError("Approve the prompt before submitting production.")
        job = project_service.repository.get_production_job(existing.response["job_id"]) if existing is not None and hasattr(project_service.repository, "get_production_job") else None
        if job is None:
            job = production_service.submit_clip(project, scene_number, project_service.repository)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if existing is None and hasattr(project_service.repository, "save_idempotency"):
        from app.domain.integration import IdempotencyRecord
        from datetime import datetime, timezone
        project_service.repository.save_idempotency(IdempotencyRecord(idempotency_key, "integration.production", request_hash, {"job_id": job.job_id}, datetime.now(timezone.utc)))
    if request_id:
        project_service._audit("integration.production_submitted", str(project_id), request_id, {"job_id": job.job_id, "scene_number": scene_number, "prompt_version": job.prompt_version})
    return _production_response(job)


@router.get(
    "/api/integrations/production-jobs/{job_id}",
    response_model=ProductionJobResponse,
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_production_status(job_id: str) -> ProductionJobResponse:
    job = getattr(project_service.repository, "get_production_job", lambda _: None)(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Production job not found")
    return _production_response(job)


@router.post(
    "/api/integrations/production-jobs/{job_id}/callback",
    response_model=ProductionJobResponse,
    tags=["integrations"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_production_callback(job_id: str, payload: dict) -> ProductionJobResponse:
    job = getattr(project_service.repository, "get_production_job", lambda _: None)(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Production job not found")
    try:
        job = production_service.complete_callback(job, payload, project_service.repository)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _production_response(job)
