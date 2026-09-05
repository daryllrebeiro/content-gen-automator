from uuid import UUID, uuid4
import os
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, BackgroundTasks, Response
import time

from app.schemas.health import HealthResponse, ReadinessResponse
from app.config import settings
from app.schemas.projects import (
    ClipReviewRequest,
    ClipReviewResponse,
    FactResponse,
    ExportResponse,
    FinalReviewRequest,
    FinalReviewResponse,
    FinalReviewStatusResponse,
    GateReportResponse,
    MetadataValidationResponse,
    ProjectCreateRequest,
    ProjectResponse,
    PromptResponse,
    PublishingResponse,
    PublishRequest,
    PublishResponse,
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
    YouTubeUploadJobResponse,
    PlatformExportResponse,
)
from app.domain.project import ProjectInput, Platform
from app.domain.integration import (
    ClipReviewEvent,
    FinalReviewEvent,
    YouTubeUploadJob,
)
from app.services.project_service import (
    ProjectNotFoundError,
    ProjectService,
    ProjectStateError,
)
from app.services.export_service import ExportService
from app.api.integration_auth import require_integration_auth
from app.services.delivery_service import DeliveryService
from app.services.production_service import ProductionService
from app.services.publishing_gate_service import PublishingGateService
from app.services.youtube_metadata_validator import YouTubeMetadataValidator
from app.adapters.grafana_telemetry import telemetry
from app.adapters.parallel_search import parallel_search
from app.adapters.clickhouse_analytics import clickhouse_analytics
from app.adapters.ibm_governance import ibm_governance
from app.agents.orchestrator_agent import orchestrator_agent
from app.services.compliance_certificate_service import compliance_certificate_service
from app.api.byok import (
    ByokCredentials,
    ByokVerifyRequest,
    get_byok_credentials,
    resolve_gemini_key,
    resolve_video_provider_key,
    verify_gemini_key,
    is_byok_enforced,
)


router = APIRouter()
project_service = ProjectService()
export_service = ExportService()
delivery_service = DeliveryService()
production_service = ProductionService()
publishing_gate_service = PublishingGateService()
youtube_metadata_validator = YouTubeMetadataValidator()


def run_production_pipeline_async(
    project_id_str: str,
    job_id: str,
    scene_number: int,
    tts_api_key: Optional[str] = None,
    video_api_key: Optional[str] = None,
):
    repo = project_service.repository
    project = repo.get(UUID(project_id_str))
    prompt = project.prompts.get(scene_number)
    if not prompt:
        return

    job = None
    if hasattr(repo, "get_production_job"):
        job = repo.get_production_job(job_id)
    else:
        if hasattr(repo, "production_jobs"):
            job = repo.production_jobs.get(job_id)

    if not job:
        return

    time.sleep(1.5)

    try:
        audio_url = f"/static/audio/{project_id_str}_{scene_number}.mp3"
        if project.input.tts_provider == "elevenlabs":
            from app.services.elevenlabs_service import ElevenLabsTTSService
            tts_service = ElevenLabsTTSService()
            tts_service.synthesize(project_id_str, scene_number, prompt.narration, api_key=tts_api_key)
        else:
            import os
            os.makedirs("app/static/audio", exist_ok=True)
            with open(f"app/static/audio/{project_id_str}_{scene_number}.mp3", "wb") as f:
                f.write(b"MOCK AUDIO DATA")
        
        video_url = f"/static/video/{project_id_str}_{scene_number}.mp4"
        if project.input.video_provider in {"runway", "kling", "gemini_omni"}:
            from app.services.video_gen_service import RealVideoGenService
            video_service = RealVideoGenService()
            video_service.generate_clip(project_id_str, scene_number, prompt.text, project.input.video_provider, api_key=video_api_key)
        else:
            import os
            os.makedirs("app/static/video", exist_ok=True)
            with open(f"app/static/video/{project_id_str}_{scene_number}.mp4", "wb") as f:
                f.write(b"MOCK VIDEO DATA")

        payload = {
            "status": "SUCCEEDED",
            "duration_seconds": 10,
            "aspect_ratio": "9:16",
            "narration_end_seconds": 8.5,
            "checksum": hashlib.sha256(f"{project_id_str}:{scene_number}".encode()).hexdigest()[:16],
            "artifact_url": video_url,
        }
        production_service.complete_callback(job, payload, repo)
    except Exception as e:
        payload = {
            "status": "FAILED_PERMANENT",
            "error": str(e),
        }
        production_service.complete_callback(job, payload, repo)


def run_publishing_pipeline_async(project_id_str: str, upload_job_id: str):
    repo = project_service.repository
    project = repo.get(UUID(project_id_str))
    
    upload_job = None
    if hasattr(repo, "get_youtube_upload_job"):
        upload_job = repo.get_youtube_upload_job(upload_job_id)
    else:
        if hasattr(repo, "youtube_upload_jobs"):
            upload_job = repo.youtube_upload_jobs.get(upload_job_id)

    if not upload_job:
        return
        
    upload_job.status = "UPLOADING"
    if hasattr(repo, "save_youtube_upload_job"):
        repo.save_youtube_upload_job(upload_job)

    try:
        final_video_url = f"/static/output/{project_id_str}_final.mp4"
        from app.services.ffmpeg_service import FFmpegAssemblyService
        stitcher = FFmpegAssemblyService()
        if project.input.stitch_provider == "ffmpeg":
            stitcher.assemble_shorts(project)
        else:
            import os
            os.makedirs("app/static/output", exist_ok=True)
            with open(f"app/static/output/{project_id_str}_final.mp4", "wb") as f:
                f.write(b"MOCK FINAL STITCHED VIDEO")

        # 1. Multi-platform media export fan-out
        target_platforms = getattr(project.input, "target_platforms", [Platform.YOUTUBE_SHORTS])
        dry_run = (project.input.stitch_provider != "ffmpeg")
        stitcher.export_platform_targets(
            project,
            platforms=target_platforms,
            input_video_path=f"app/static/output/{project_id_str}_final.mp4",
            dry_run=dry_run
        )

        # 2. Modular publishing per target platform
        from app.services.publish_adapters import get_publish_adapter
        youtube_url = "https://youtu.be/dQw4w9WgXcQ"
        for plat in target_platforms:
            plat_key = plat.value if hasattr(plat, "value") else str(plat)
            adapter = get_publish_adapter(plat)
            export_rec = project.platform_exports.get(plat_key)
            asset_ref = export_rec.output_asset_ref if export_rec else f"app/static/output/{project_id_str}_final.mp4"
            pub_res = adapter.publish(project, asset_ref)
            if export_rec:
                export_rec.publish_status = pub_res.status
                export_rec.publish_asset_ref = pub_res.published_url or pub_res.package_dir
                export_rec.publish_metadata = pub_res.manifest or {"message": pub_res.message}
            if plat_key == Platform.YOUTUBE_SHORTS.value and pub_res.published_url:
                youtube_url = pub_res.published_url

        upload_job.youtube_video_id = youtube_url.split("/")[-1]
        upload_job.youtube_url = youtube_url
        upload_job.published_at = datetime.now(timezone.utc)
        upload_job.status = "PUBLISHED"
        upload_job.error = ""
        upload_job.error_class = ""
        project.status = project.status.__class__.PUBLISHED
        repo.save(project)
    except Exception as e:
        upload_job.status = "FAILED_PERMANENT"
        upload_job.error = str(e)
        upload_job.error_class = e.__class__.__name__
        project.status = project.status.__class__.PUBLISH_FAILED
        repo.save(project)

    if hasattr(repo, "save_youtube_upload_job"):
        repo.save_youtube_upload_job(upload_job)



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
        tts_provider=project.input.tts_provider,
        video_provider=project.input.video_provider,
        stitch_provider=project.input.stitch_provider,
        publish_provider=project.input.publish_provider,
        target_platforms=[
            p.value if hasattr(p, "value") else str(p)
            for p in getattr(project.input, "target_platforms", [Platform.YOUTUBE_SHORTS])
        ],
        model_tier=getattr(project.input, "model_tier", "flagship"),
        platform_exports={
            k: PlatformExportResponse(
                platform=v.platform.value if hasattr(v.platform, "value") else str(v.platform),
                aspect_ratio=v.aspect_ratio,
                output_asset_ref=v.output_asset_ref,
                export_status=v.export_status,
                publish_status=v.publish_status,
                publish_asset_ref=v.publish_asset_ref,
                publish_metadata=v.publish_metadata or {},
            )
            for k, v in getattr(project, "platform_exports", {}).items()
        },
    )



@router.post("/api/projects", response_model=ProjectResponse, tags=["projects"])
def create_project(request: ProjectCreateRequest) -> ProjectResponse:
    target_platforms = [
        Platform(p) if isinstance(p, str) else p
        for p in request.target_platforms
    ] if request.target_platforms else [Platform.YOUTUBE_SHORTS]

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
            autonomous=request.autonomous,
            tts_provider=request.tts_provider,
            video_provider=request.video_provider,
            stitch_provider=request.stitch_provider,
            publish_provider=request.publish_provider,
            token_budget=request.token_budget,
            target_platforms=target_platforms,
            model_tier=request.model_tier,
        )
    )
    # Partner Integrations: Grafana Observability + ClickHouse Analytics
    telemetry.record_project_created(request.topic)
    clickhouse_analytics.log_event("project_created", str(project.id), {"topic": request.topic, "tone": request.tone})
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
def generate_first_prompt(
    project_id: UUID,
    byok: ByokCredentials = Depends(get_byok_credentials)
) -> PromptResponse:
    try:
        t0 = time.time()
        project = project_service.repository.get(project_id)
        current_scene_idx = len(project.prompts) + 1
        model_tier = getattr(project.input, "model_tier", "flagship")
        gemini_key = resolve_gemini_key(byok)

        # Enforce BYOK in production for real Gemini provider
        if is_byok_enforced() and os.getenv("LLM_PROVIDER", "mock").lower() == "gemini" and not gemini_key:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "BYOK_KEY_REQUIRED",
                    "provider": "gemini",
                    "message": (
                        "Generating content with Google Gemini requires your Gemini API key in Studio BYOK settings. "
                        "Click '🔑 API Keys' in the top bar to configure your key, or run in Simulated Studio (Mock) mode."
                    ),
                    "action_url": "https://aistudio.google.com/apikey"
                }
            )

        # 1. Coordinate reasoning via ADK Multi-Agent Orchestrator
        agent_trace = orchestrator_agent.orchestrate_scene_generation(
            project_id=str(project_id),
            topic=project.input.topic,
            scene_number=current_scene_idx,
            total_scenes=len(project.scenes),
            tone=project.input.tone or "cinematic",
            facts=project.input.facts or [],
            model_tier=model_tier,
            gemini_api_key=gemini_key,
        )

        # 2. Advance Domain FSM & Generate Prompt
        prompt = project_service.generate_next(project_id, gemini_api_key=gemini_key)
        latency = time.time() - t0
        
        # 3. IBM watsonx Governance Compliance Gate (Enforced & Blocking)
        gov_audit = ibm_governance.audit_prompt(
            prompt_text=f"{project.input.topic} {prompt.text}",
            project_id=str(project_id)
        )
        if gov_audit.get("decision") != "passed":
            raise HTTPException(
                status_code=422,
                detail=f"IBM watsonx.governance safety violation: {gov_audit.get('policy_checks', {}).get('brand_safety') or gov_audit.get('copyright_risk') or 'High risk score'}. Scene progression halted."
            )

        # 4. Partner Telemetry Collection
        telemetry.record_prompt_generation(
            duration_seconds=latency,
            input_tokens=prompt.estimated_input_tokens or 250,
            output_tokens=prompt.estimated_output_tokens or 150,
            project_id=str(project_id)
        )
        clickhouse_analytics.log_scene_telemetry(
            project_id=str(project_id),
            scene_number=prompt.scene_number,
            version=prompt.version_number,
            word_count=prompt.narration_word_count,
            tone="cinematic"
        )
        return _prompt_response(prompt)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/api/projects/{project_id}/prompts/next",
    response_model=PromptResponse,
    tags=["prompts"],
)
def generate_next_prompt(
    project_id: UUID,
    byok: ByokCredentials = Depends(get_byok_credentials)
) -> PromptResponse:
    return generate_first_prompt(project_id, byok=byok)


@router.post(
    "/api/projects/{project_id}/prompts/{scene_number}/regenerate",
    response_model=PromptResponse,
    tags=["prompts"],
)
def regenerate_prompt(
    project_id: UUID,
    scene_number: int,
    byok: ByokCredentials = Depends(get_byok_credentials)
) -> PromptResponse:
    try:
        t0 = time.time()
        project = project_service.repository.get(project_id)
        model_tier = getattr(project.input, "model_tier", "flagship")
        gemini_key = resolve_gemini_key(byok)

        if is_byok_enforced() and os.getenv("LLM_PROVIDER", "mock").lower() == "gemini" and not gemini_key:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "BYOK_KEY_REQUIRED",
                    "provider": "gemini",
                    "message": "Regenerating content with Google Gemini requires your Gemini API key in Studio BYOK settings.",
                    "action_url": "https://aistudio.google.com/apikey"
                }
            )

        # ADK Orchestration trace
        orchestrator_agent.orchestrate_scene_generation(
            project_id=str(project_id),
            topic=project.input.topic,
            scene_number=scene_number,
            total_scenes=len(project.scenes),
            tone="regenerated",
            model_tier=model_tier,
            gemini_api_key=gemini_key,
        )

        prompt = project_service.regenerate(project_id, scene_number, gemini_api_key=gemini_key)
        latency = time.time() - t0
        
        # IBM watsonx Governance gate check
        gov_audit = ibm_governance.audit_prompt(prompt.text, project_id=str(project_id))
        if gov_audit.get("decision") != "passed":
            raise HTTPException(
                status_code=422,
                detail=f"IBM watsonx.governance safety violation: {gov_audit.get('copyright_risk') or 'High risk score'}. Regeneration halted."
            )

        telemetry.record_prompt_generation(
            duration_seconds=latency,
            input_tokens=prompt.estimated_input_tokens or 300,
            output_tokens=prompt.estimated_output_tokens or 180,
            project_id=str(project_id)
        )
        clickhouse_analytics.log_scene_telemetry(
            project_id=str(project_id),
            scene_number=prompt.scene_number,
            version=prompt.version_number,
            word_count=prompt.narration_word_count,
            tone="regenerated"
        )
        return _prompt_response(prompt)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/api/projects/{project_id}/compliance-certificate",
    tags=["governance"],
)
def get_project_compliance_certificate(project_id: UUID):
    try:
        project = project_service.repository.get(project_id)
        audit_records = [
            ibm_governance.audit_prompt(prompt.text, project_id=str(project_id))
            for prompt in project.prompts.values()
        ] if project.prompts else [
            ibm_governance.audit_prompt(f"Scene for topic: {project.input.topic}", project_id=str(project_id))
        ]
        certificate = compliance_certificate_service.generate_certificate(
            project_id=str(project_id),
            topic=project.input.topic,
            policy_pack_id="general_audience",
            audit_records=audit_records,
            manifest_id=f"manifest-{str(project_id)[:8]}"
        )
        certificate["is_signature_valid"] = compliance_certificate_service.verify_certificate(certificate)
        return certificate
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.get(
    "/api/projects/{project_id}/compliance-certificate/download",
    tags=["governance"],
)
def download_project_compliance_certificate(project_id: UUID):
    """Downloads the signed Compliance Certificate as a formatted JSON document."""
    cert = get_project_compliance_certificate(project_id)
    content = json.dumps(cert, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=compliance-certificate-{project_id}.json"}
    )


@router.post(
    "/api/governance/verify-certificate",
    tags=["governance"],
)
def verify_certificate_authenticity(cert: Dict[str, Any]):
    """Verifies the HMAC-SHA256 signature of any submitted Compliance Certificate."""
    is_valid = compliance_certificate_service.verify_certificate(cert)
    return {
        "is_valid": is_valid,
        "certificate_id": cert.get("certificate_id", "UNKNOWN"),
        "verdict": "AUTHENTIC_VERIFIED" if is_valid else "TAMPER_DETECTED_INVALID",
        "signature_algorithm": cert.get("signature_algorithm", "HMAC-SHA256"),
        "verified_at": datetime.now(timezone.utc).isoformat()
    }


@router.get(
    "/api/governance/policy-packs",
    tags=["governance"],
)
def list_governance_policy_packs():
    """Lists all available IBM watsonx governance policy packs and their risk thresholds."""
    from app.services.policy_pack_service import policy_pack_service
    return [p.model_dump() for p in policy_pack_service.list_policy_packs()]


@router.post(
    "/api/governance/policy-packs",
    tags=["governance"],
)
def create_governance_policy_pack(pack: Dict[str, Any]):
    """Registers or updates a custom IBM watsonx governance policy pack."""
    from app.services.policy_pack_service import policy_pack_service, GovernancePolicyPack
    model = GovernancePolicyPack(**pack)
    return policy_pack_service.create_policy_pack(model).model_dump()


@router.post(
    "/api/governance/advisor",
    tags=["governance"],
)
def governance_advisory_check(payload: Dict[str, Any]):
    """Provides soft real-time inline safety suggestions for draft prompts before submission."""
    prompt_text = payload.get("prompt_text", "")
    policy_pack = payload.get("policy_pack", "general_audience")
    audit = ibm_governance.audit_prompt(prompt_text, policy_pack=policy_pack)
    advisories = []
    if audit["risk_score"] > 0.10:
        advisories.append("Risk score approaching policy ceiling; review tone and intensity.")
    if audit.get("policy_checks", {}).get("copyright_risk") != "negligible":
        advisories.append("Potential trademark or copyright reference detected; use generic equivalents.")
    return {
        "status": "advisory",
        "decision": audit["decision"],
        "risk_score": audit["risk_score"],
        "policy_pack": policy_pack,
        "advisory_warnings": advisories,
        "is_safe_to_submit": audit["decision"] == "passed"
    }


@router.get(
    "/api/telemetry/budget-status/{project_id}",
    tags=["telemetry"],
)
def get_project_budget_status(project_id: UUID):
    """Returns token consumption, budget ceiling, and remaining headroom for FinOps monitoring."""
    try:
        project = project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    budget = getattr(project.input, "token_budget", 50000)
    consumed = telemetry.get_project_token_usage(str(project_id))
    headroom = max(0, budget - consumed)
    pct = round((consumed / max(1, budget)) * 100, 1)
    return {
        "project_id": str(project_id),
        "token_budget": budget,
        "tokens_consumed": consumed,
        "budget_headroom": headroom,
        "percent_used": pct,
        "cost_ceiling_exceeded": consumed > budget
    }


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
    "/api/projects/{project_id}/exports/manifest",
    response_model=ExportManifestResponse,
    tags=["export"],
)
def public_create_export_manifest(project_id: UUID) -> ExportManifestResponse:
    try:
        project = project_service.repository.get(project_id)
        manifest = delivery_service.create_manifest(project, project_service.repository, export_service)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    return _manifest_response(manifest)



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
                autonomous=request.autonomous,
                tts_provider=request.tts_provider,
                video_provider=request.video_provider,
                stitch_provider=request.stitch_provider,
                publish_provider=request.publish_provider,
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


# ---------------------------------------------------------------------------
# Sprint 0 — Public prompt approve/reject routes (no auth; dev-only convenience)
# These proxy to the same project_service.decide_prompt() used by integration routes.
# ---------------------------------------------------------------------------

@router.post(
    "/api/projects/{project_id}/prompts/{scene_number}/approve",
    response_model=ApprovalResponse,
    tags=["prompts"],
)
def public_approve_prompt(project_id: UUID, scene_number: int, request: ApprovalRequest) -> ApprovalResponse:
    try:
        project = project_service.decide_prompt(project_id, scene_number, decision="approved", actor=request.actor, comment=request.comment)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    project_service._audit("prompt.approved", str(project_id), metadata={"scene_number": scene_number, "actor": request.actor})
    return ApprovalResponse(project_id=project.id, scene_number=scene_number, decision="approved", status=project.status.value)


@router.post(
    "/api/projects/{project_id}/prompts/{scene_number}/reject",
    response_model=ApprovalResponse,
    tags=["prompts"],
)
def public_reject_prompt(project_id: UUID, scene_number: int, request: ApprovalRequest) -> ApprovalResponse:
    try:
        project = project_service.decide_prompt(project_id, scene_number, decision="rejected", actor=request.actor, comment=request.comment)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    project_service._audit("prompt.rejected", str(project_id), metadata={"scene_number": scene_number, "actor": request.actor})
    return ApprovalResponse(project_id=project.id, scene_number=scene_number, decision="rejected", status=project.status.value)


# ---------------------------------------------------------------------------
# Phase 8 — Clip review endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/api/integrations/projects/{project_id}/clips/{scene_number}/review",
    response_model=ClipReviewResponse,
    tags=["publishing"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_review_clip(
    project_id: UUID,
    scene_number: int,
    request: ClipReviewRequest,
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> ClipReviewResponse:
    try:
        project = project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    # Verify artifact belongs to this project/scene
    artifact = getattr(project_service.repository, "get_clip_artifact", lambda _: None)(request.artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Clip artifact not found")

    # Update artifact review_status
    artifact.review_status = request.decision
    if hasattr(project_service.repository, "save_clip_artifact"):
        project_service.repository.save_clip_artifact(artifact)

    # Record the review event
    event_id = hashlib.sha256(
        f"clip_review:{project_id}:{scene_number}:{request.artifact_id}:{request.decision}:{datetime.now(timezone.utc).timestamp()}".encode()
    ).hexdigest()[:24]
    event = ClipReviewEvent(
        event_id=event_id,
        project_id=str(project_id),
        scene_number=scene_number,
        artifact_id=request.artifact_id,
        decision=request.decision,
        actor=request.actor,
        comment=request.comment,
        created_at=datetime.now(timezone.utc),
    )
    if hasattr(project_service.repository, "save_clip_review_event"):
        project_service.repository.save_clip_review_event(event)

    project_service._audit(
        f"clip.{request.decision}", str(project_id), request_id,
        {"scene_number": scene_number, "artifact_id": request.artifact_id, "actor": request.actor},
    )
    return ClipReviewResponse(
        project_id=project_id,
        scene_number=scene_number,
        artifact_id=request.artifact_id,
        decision=request.decision,
        actor=request.actor,
        status=request.decision,
    )


# ---------------------------------------------------------------------------
# Phase 8 — Final review endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/api/integrations/projects/{project_id}/final-review",
    response_model=FinalReviewStatusResponse,
    tags=["publishing"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_get_final_review(project_id: UUID) -> FinalReviewStatusResponse:
    try:
        project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    review = getattr(project_service.repository, "get_latest_final_review", lambda _: None)(str(project_id))
    if review is None:
        return FinalReviewStatusResponse(project_id=project_id, has_review=False, decision=None, actor=None, manifest_id=None, comment=None)
    return FinalReviewStatusResponse(project_id=project_id, has_review=True, decision=review.decision, actor=review.actor, manifest_id=review.manifest_id, comment=review.comment)


def _submit_final_review(project_id: UUID, decision: str, request: FinalReviewRequest, request_id: str | None) -> FinalReviewResponse:
    try:
        project = project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    manifest = getattr(project_service.repository, "get_export_manifest", lambda _: None)(request.manifest_id)
    if manifest is None or manifest.project_id != str(project_id):
        raise HTTPException(status_code=404, detail="Export manifest not found for this project")

    event_id = hashlib.sha256(
        f"final_review:{project_id}:{decision}:{request.actor}:{datetime.now(timezone.utc).timestamp()}".encode()
    ).hexdigest()[:24]
    event = FinalReviewEvent(
        event_id=event_id,
        project_id=str(project_id),
        manifest_id=request.manifest_id,
        decision=decision,
        actor=request.actor,
        comment=request.comment,
        created_at=datetime.now(timezone.utc),
    )
    if hasattr(project_service.repository, "save_final_review_event"):
        project_service.repository.save_final_review_event(event)

    # Advance project status
    if decision == "approved":
        project.status = project.status.__class__.VIDEO_APPROVED
    else:
        project.status = project.status.__class__.VIDEO_REJECTED
    project_service.repository.save(project)

    project_service._audit(f"final_review.{decision}", str(project_id), request_id, {"actor": request.actor, "manifest_id": request.manifest_id})
    return FinalReviewResponse(project_id=project_id, decision=decision, actor=request.actor, manifest_id=request.manifest_id, project_status=project.status.value)


@router.post(
    "/api/integrations/projects/{project_id}/final-review/approve",
    response_model=FinalReviewResponse,
    tags=["publishing"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_approve_final(
    project_id: UUID,
    request: FinalReviewRequest,
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> FinalReviewResponse:
    return _submit_final_review(project_id, "approved", request, request_id)


@router.post(
    "/api/integrations/projects/{project_id}/final-review/reject",
    response_model=FinalReviewResponse,
    tags=["publishing"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_reject_final(
    project_id: UUID,
    request: FinalReviewRequest,
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> FinalReviewResponse:
    return _submit_final_review(project_id, "rejected", request, request_id)


# ---------------------------------------------------------------------------
# Phase 8 — Publishing gate check
# ---------------------------------------------------------------------------

@router.get(
    "/api/integrations/projects/{project_id}/publish/gate",
    response_model=GateReportResponse,
    tags=["publishing"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_gate_check(project_id: UUID) -> GateReportResponse:
    try:
        project = project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    report = publishing_gate_service.check(project, project_service.repository)
    return GateReportResponse(can_publish=report.can_publish, failed_gates=report.failed_gates)


# ---------------------------------------------------------------------------
# Phase 8 — Publish (creates YouTube upload job after gate check)
# ---------------------------------------------------------------------------

@router.post(
    "/api/integrations/projects/{project_id}/publish",
    response_model=PublishResponse,
    tags=["publishing"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_publish(
    project_id: UUID,
    request: PublishRequest,
    background_tasks: BackgroundTasks,
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> PublishResponse:
    try:
        project = project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    # Mock enterprise RBAC check on final publishing gate
    if request.actor.lower() == "guest" or "intern" in request.actor.lower():
        raise HTTPException(status_code=403, detail="Enterprise RBAC: Actor does not have publish permissions.")

    # Idempotency check
    existing_key = getattr(project_service.repository, "get_idempotency", lambda _: None)(request.idempotency_key)
    if existing_key is not None:
        if existing_key.operation != "integration.publish":
            raise HTTPException(status_code=409, detail="Idempotency key was reused with a different operation.")
        existing_job = getattr(project_service.repository, "get_youtube_upload_job", lambda _: None)(existing_key.response.get("job_id", ""))
        if existing_job is not None:
            return PublishResponse(job_id=existing_job.job_id, project_id=project_id, manifest_id=existing_job.manifest_id, status=existing_job.status, upload_checksum=existing_job.upload_checksum)

    # Gate check — enforced in API layer, not n8n
    report = publishing_gate_service.check(project, project_service.repository)
    if not report.can_publish:
        raise HTTPException(status_code=422, detail={"message": "Pre-publish gates failed.", "failed_gates": report.failed_gates})

    # Get latest manifest
    manifest = getattr(project_service.repository, "get_latest_export_manifest", lambda _: None)(str(project_id))
    if manifest is None:
        raise HTTPException(status_code=422, detail="No export manifest found.")

    # Create upload job
    upload_checksum = hashlib.sha256(f"{manifest.checksum}:{manifest.manifest_id}".encode()).hexdigest()
    job_id = str(uuid4())
    job = YouTubeUploadJob(
        job_id=job_id,
        project_id=str(project_id),
        manifest_id=manifest.manifest_id,
        status="QUEUED",
        upload_checksum=upload_checksum,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    if hasattr(project_service.repository, "save_youtube_upload_job"):
        project_service.repository.save_youtube_upload_job(job)

    # Advance project status
    project.status = project.status.__class__.PUBLISHING_PENDING
    project_service.repository.save(project)

    # Record idempotency
    from app.domain.integration import IdempotencyRecord
    if hasattr(project_service.repository, "save_idempotency"):
        project_service.repository.save_idempotency(IdempotencyRecord(request.idempotency_key, "integration.publish", hashlib.sha256(f"publish:{project_id}".encode()).hexdigest(), {"job_id": job_id}, datetime.now(timezone.utc)))

    # Trigger background task if real providers are used or project is in autonomous autopilot mode
    if project.input.publish_provider != "mock" or project.input.stitch_provider != "mock" or project.input.autonomous:
        background_tasks.add_task(run_publishing_pipeline_async, str(project_id), job_id)

    project_service._audit("project.publish_queued", str(project_id), request_id, {"job_id": job_id, "actor": request.actor, "upload_checksum": upload_checksum})
    return PublishResponse(job_id=job_id, project_id=project_id, manifest_id=manifest.manifest_id, status="QUEUED", upload_checksum=upload_checksum)


# ---------------------------------------------------------------------------
# Phase 8 — YouTube upload job status & n8n callback
# ---------------------------------------------------------------------------

def _upload_job_response(job) -> YouTubeUploadJobResponse:
    return YouTubeUploadJobResponse(
        job_id=job.job_id,
        project_id=UUID(job.project_id),
        manifest_id=job.manifest_id,
        status=job.status,
        youtube_video_id=job.youtube_video_id,
        upload_attempts=job.upload_attempts,
        error_class=job.error_class,
        youtube_url=job.youtube_url,
        error=job.error,
    )


@router.get(
    "/api/integrations/youtube-upload-jobs/{job_id}",
    response_model=YouTubeUploadJobResponse,
    tags=["publishing"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_upload_job_status(job_id: str) -> YouTubeUploadJobResponse:
    job = getattr(project_service.repository, "get_youtube_upload_job", lambda _: None)(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="YouTube upload job not found")
    return _upload_job_response(job)


@router.post(
    "/api/integrations/youtube-upload-jobs/{job_id}/callback",
    response_model=YouTubeUploadJobResponse,
    tags=["publishing"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_upload_job_callback(
    job_id: str,
    payload: dict,
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> YouTubeUploadJobResponse:
    job = getattr(project_service.repository, "get_youtube_upload_job", lambda _: None)(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="YouTube upload job not found")

    if job.status in {"PUBLISHED", "FAILED_PERMANENT"}:
        return _upload_job_response(job)  # idempotent

    status = str(payload.get("status", "")).upper()
    if status not in {"PUBLISHED", "FAILED_RETRYABLE", "FAILED_PERMANENT"}:
        raise HTTPException(status_code=422, detail=f"Unsupported callback status: {status}")

    job.upload_attempts += 1
    job.status = status
    job.updated_at = datetime.now(timezone.utc)

    if status == "PUBLISHED":
        job.youtube_video_id = str(payload.get("youtube_video_id", ""))
        job.youtube_url = str(payload.get("youtube_url", ""))
        job.published_at = datetime.now(timezone.utc)
        job.error = ""
        job.error_class = ""
        # Advance project to PUBLISHED
        try:
            project = project_service.repository.get(UUID(job.project_id))
            project.status = project.status.__class__.PUBLISHED
            project_service.repository.save(project)
        except ProjectNotFoundError:
            pass
    else:
        job.error = str(payload.get("error", ""))
        job.error_class = str(payload.get("error_class", ""))
        if status == "FAILED_PERMANENT":
            try:
                project = project_service.repository.get(UUID(job.project_id))
                project.status = project.status.__class__.PUBLISH_FAILED
                project_service.repository.save(project)
            except ProjectNotFoundError:
                pass

    if hasattr(project_service.repository, "save_youtube_upload_job"):
        project_service.repository.save_youtube_upload_job(job)

    project_service._audit(f"upload.{status.lower()}", job.project_id, request_id, {"job_id": job_id, "youtube_video_id": job.youtube_video_id})
    return _upload_job_response(job)


# ---------------------------------------------------------------------------
# Phase 8 — YouTube metadata validation
# ---------------------------------------------------------------------------

@router.post(
    "/api/integrations/projects/{project_id}/metadata/validate",
    response_model=MetadataValidationResponse,
    tags=["publishing"],
    dependencies=[Depends(require_integration_auth)],
)
def integration_validate_metadata(project_id: UUID) -> MetadataValidationResponse:
    try:
        project = project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    publishing_package = export_service.publishing_package(project)
    report = youtube_metadata_validator.validate(publishing_package)
    return MetadataValidationResponse(valid=report.valid, errors=report.errors, warnings=report.warnings)


# ---------------------------------------------------------------------------
# Public / Dev-friendly endpoints for production, clip review, and publishing
# ---------------------------------------------------------------------------

@router.post(
    "/api/projects/{project_id}/scenes/{scene_number}/production",
    response_model=ProductionJobResponse,
    tags=["production"],
)
def public_submit_production(
    project_id: UUID,
    scene_number: int,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    byok: ByokCredentials = Depends(get_byok_credentials),
) -> ProductionJobResponse:
    ikey = idempotency_key or f"prod-scene-{project_id}-{scene_number}-{datetime.now(timezone.utc).timestamp()}"
    request_hash = hashlib.sha256(f"public.production:{project_id}:{scene_number}".encode()).hexdigest()
    
    existing = getattr(project_service.repository, "get_idempotency", lambda _: None)(ikey)
    if existing is not None and (existing.operation != "public.production" or existing.request_hash != request_hash):
        raise HTTPException(status_code=409, detail="Idempotency key was reused with a different request.")
    
    try:
        project = project_service.repository.get(project_id)
        if project.status not in {project.status.APPROVED, project.status.COMPLETED}:
            raise ProjectStateError("Approve the prompt before submitting production.")
        
        # Enterprise Cost-Ceiling Guardrail
        budget = getattr(project.input, "token_budget", 50000)
        is_exceeded, consumed, limit = telemetry.is_cost_ceiling_exceeded(str(project_id), budget)
        if is_exceeded:
            raise HTTPException(
                status_code=429,
                detail=f"Cost ceiling exceeded: Project token consumption ({consumed}) reached budget limit ({limit} tokens). Auto-Pilot render halted."
            )

        video_key = resolve_video_provider_key(project.input.video_provider, byok)
        tts_key = byok.elevenlabs

        if is_byok_enforced():
            if project.input.video_provider in {"runway", "kling", "gemini_omni"} and not video_key:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "BYOK_KEY_REQUIRED",
                        "provider": project.input.video_provider,
                        "message": f"Rendering clips with {project.input.video_provider} requires your API key in Studio BYOK settings.",
                    }
                )
            if project.input.tts_provider == "elevenlabs" and not tts_key:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "BYOK_KEY_REQUIRED",
                        "provider": "elevenlabs",
                        "message": "Generating voiceover with ElevenLabs requires your ElevenLabs API key in Studio BYOK settings.",
                    }
                )

        job = project_service.repository.get_production_job(existing.response["job_id"]) if existing is not None and hasattr(project_service.repository, "get_production_job") else None
        if job is None:
            job = production_service.submit_clip(project, scene_number, project_service.repository)
            # Trigger background task if real providers are used or project is in autonomous autopilot mode
            if project.input.tts_provider != "mock" or project.input.video_provider != "mock" or project.input.autonomous:
                background_tasks.add_task(
                    run_production_pipeline_async,
                    str(project_id),
                    job.job_id,
                    scene_number,
                    tts_api_key=tts_key,
                    video_api_key=video_key,
                )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    
    if existing is None and hasattr(project_service.repository, "save_idempotency"):
        from app.domain.integration import IdempotencyRecord
        project_service.repository.save_idempotency(IdempotencyRecord(ikey, "public.production", request_hash, {"job_id": job.job_id}, datetime.now(timezone.utc)))
    
    return _production_response(job)



@router.post(
    "/api/projects/{project_id}/production-jobs/{job_id}/mock-complete",
    response_model=ProductionJobResponse,
    tags=["production"],
)
def public_mock_complete_production(project_id: UUID, job_id: str) -> ProductionJobResponse:
    job = getattr(project_service.repository, "get_production_job", lambda _: None)(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Production job not found")
    
    payload = {
        "status": "SUCCEEDED",
        "duration_seconds": 10,
        "aspect_ratio": "9:16",
        "narration_end_seconds": 8.5,
        "checksum": f"mock-checksum-{uuid4().hex[:8]}",
        "artifact_url": f"https://storage.googleapis.com/mock-bucket/project-{project_id}-scene-{job.scene_number}.mp4",
    }
    try:
        job = production_service.complete_callback(job, payload, project_service.repository)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _production_response(job)


@router.get(
    "/api/projects/{project_id}/production-jobs",
    response_model=list[ProductionJobResponse],
    tags=["production"],
)
def public_get_production_jobs(project_id: UUID) -> list[ProductionJobResponse]:
    try:
        project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    
    # Query repository production jobs
    jobs = []
    repo = project_service.repository
    if hasattr(repo, "production_jobs"):
        # InMemory
        jobs = [j for j in repo.production_jobs.values() if j.project_id == str(project_id)]
    elif hasattr(repo, "engine"):
        # SQL repo
        from sqlalchemy import select as sa_select
        from app.repositories.sql import Session, ProductionJobRecord
        with Session(repo.engine) as session:
            records = session.scalars(
                sa_select(ProductionJobRecord).where(ProductionJobRecord.project_id == str(project_id))
            ).all()
            from app.domain.integration import ProductionJob as PJ
            jobs = [PJ(r.job_id, r.project_id, r.scene_number, r.prompt_version, r.job_type, r.provider, r.provider_job_id, r.status, r.contract or {}, r.artifact_id, r.error, r.created_at, r.updated_at) for r in records]
    
    return [_production_response(j) for j in sorted(jobs, key=lambda x: x.scene_number)]


@router.get(
    "/api/projects/{project_id}/clips",
    tags=["production"],
)
def public_get_clips(project_id: UUID):
    try:
        project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    
    repo = project_service.repository
    if hasattr(repo, "get_clip_artifacts_for_project"):
        artifacts = repo.get_clip_artifacts_for_project(str(project_id))
    else:
        artifacts = []
    
    return [
        {
            "artifact_id": a.artifact_id,
            "job_id": a.job_id,
            "checksum": a.checksum,
            "duration_seconds": a.duration_seconds,
            "aspect_ratio": a.aspect_ratio,
            "narration_end_seconds": a.narration_end_seconds,
            "artifact_url": a.artifact_url,
            "review_status": a.review_status,
            "created_at": a.created_at,
        }
        for a in artifacts
    ]


@router.post(
    "/api/projects/{project_id}/clips/{scene_number}/review",
    response_model=ClipReviewResponse,
    tags=["publishing"],
)
def public_review_clip(project_id: UUID, scene_number: int, request: ClipReviewRequest) -> ClipReviewResponse:
    # Proxies to the integration clip review logic
    return integration_review_clip(project_id, scene_number, request, request_id=None)


@router.get(
    "/api/projects/{project_id}/final-review",
    response_model=FinalReviewStatusResponse,
    tags=["publishing"],
)
def public_get_final_review(project_id: UUID) -> FinalReviewStatusResponse:
    return integration_get_final_review(project_id)


@router.post(
    "/api/projects/{project_id}/final-review/approve",
    response_model=FinalReviewResponse,
    tags=["publishing"],
)
def public_approve_final(project_id: UUID, request: FinalReviewRequest) -> FinalReviewResponse:
    return _submit_final_review(project_id, "approved", request, request_id=None)


@router.post(
    "/api/projects/{project_id}/final-review/reject",
    response_model=FinalReviewResponse,
    tags=["publishing"],
)
def public_reject_final(project_id: UUID, request: FinalReviewRequest) -> FinalReviewResponse:
    return _submit_final_review(project_id, "rejected", request, request_id=None)


@router.get(
    "/api/projects/{project_id}/publish/gate",
    response_model=GateReportResponse,
    tags=["publishing"],
)
def public_gate_check(project_id: UUID) -> GateReportResponse:
    return integration_gate_check(project_id)


@router.post(
    "/api/projects/{project_id}/publish",
    response_model=PublishResponse,
    tags=["publishing"],
)
def public_publish(project_id: UUID, request: PublishRequest, background_tasks: BackgroundTasks) -> PublishResponse:
    return integration_publish(project_id, request, background_tasks, request_id=None)


@router.get(
    "/api/projects/{project_id}/youtube-upload-jobs",
    tags=["publishing"],
)
def public_get_youtube_upload_jobs(project_id: UUID):
    try:
        project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    
    repo = project_service.repository
    jobs = []
    if hasattr(repo, "youtube_upload_jobs"):
        jobs = [j for j in repo.youtube_upload_jobs.values() if j.project_id == str(project_id)]
    elif hasattr(repo, "engine"):
        from sqlalchemy import select as sa_select
        from app.repositories.sql import Session, YouTubeUploadJobRecord
        with Session(repo.engine) as session:
            records = session.scalars(
                sa_select(YouTubeUploadJobRecord).where(YouTubeUploadJobRecord.project_id == str(project_id))
            ).all()
            from app.domain.integration import YouTubeUploadJob as YJ
            jobs = [YJ(r.job_id, r.project_id, r.manifest_id, r.status, r.upload_checksum, r.youtube_video_id, r.upload_attempts, r.error_class, r.published_at, r.youtube_url, r.error, r.created_at, r.updated_at) for r in records]
            
    return [_upload_job_response(j) for j in sorted(jobs, key=lambda x: x.created_at)]


@router.post(
    "/api/projects/{project_id}/youtube-upload-jobs/{job_id}/mock-complete",
    response_model=YouTubeUploadJobResponse,
    tags=["publishing"],
)
def public_mock_complete_youtube_upload(project_id: UUID, job_id: str, success: bool = True) -> YouTubeUploadJobResponse:
    payload = {
        "status": "PUBLISHED" if success else "FAILED_PERMANENT",
        "youtube_video_id": f"yt-{uuid4().hex[:8]}" if success else "",
        "youtube_url": f"https://www.youtube.com/watch?v={uuid4().hex[:8]}" if success else "",
        "error": "" if success else "Quota exceeded or invalid credentials.",
        "error_class": "" if success else "YouTubeQuotaExceeded",
    }
    return integration_upload_job_callback(job_id, payload, request_id=None)


# ---------------------------------------------------------------------------
# Modular Platform & Model Selection Routes (Features 1 - 5)
# ---------------------------------------------------------------------------

@router.post("/api/byok/verify", tags=["byok"])
def verify_byok_key(request: ByokVerifyRequest):
    if request.provider == "gemini":
        res = verify_gemini_key(request.api_key)
        if not res.get("valid"):
            raise HTTPException(status_code=400, detail=res)
        return res
    if not request.api_key.strip():
        raise HTTPException(status_code=400, detail={"valid": False, "message": "Key cannot be empty"})
    return {"valid": True, "provider": request.provider, "message": f"{request.provider} key format accepted"}


@router.get("/api/catalog/video-providers", tags=["catalog"])
def get_video_provider_catalog(byok: ByokCredentials = Depends(get_byok_credentials)):
    from app.services.video_provider_catalog import VideoProviderCatalog
    return [p.__dict__ for p in VideoProviderCatalog.list_providers(byok=byok)]


@router.get("/api/catalog/model-tiers", tags=["catalog"])
def get_model_tier_catalog():
    from app.services.model_tier_service import ModelTierService
    return ModelTierService.list_tiers()


@router.get("/api/presets", tags=["presets"])
def list_studio_presets():
    from app.services.studio_preset_service import studio_preset_service
    return studio_preset_service.list_presets()


@router.post("/api/presets", tags=["presets"])
def create_studio_preset(data: Dict[str, Any]):
    from app.services.studio_preset_service import studio_preset_service
    if not data.get("name"):
        raise HTTPException(status_code=400, detail="Preset name is required")
    created = studio_preset_service.create_custom_preset(data)
    return created.__dict__


@router.get("/api/projects/{project_id}/platform-exports", tags=["publishing"])
def get_project_platform_exports(project_id: UUID):
    try:
        project = project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    return {
        k: {
            "platform": v.platform.value if hasattr(v.platform, "value") else str(v.platform),
            "aspect_ratio": v.aspect_ratio,
            "output_asset_ref": v.output_asset_ref,
            "export_status": v.export_status,
            "publish_status": v.publish_status,
            "publish_asset_ref": v.publish_asset_ref,
            "publish_metadata": v.publish_metadata or {},
        }
        for k, v in getattr(project, "platform_exports", {}).items()
    }


@router.get("/api/projects/{project_id}/platform-exports/{platform}/download/{file_name}", tags=["publishing"])
def download_platform_export_file(
    project_id: UUID,
    platform: str,
    file_name: str,
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    import re
    from fastapi.responses import FileResponse
    # 1. Path traversal & filename sanitation checks
    if any(sep in file_name for sep in ["..", "/", "\\", "%", "\x00"]) or not re.match(r"^[a-zA-Z0-9_.-]+$", file_name):
        raise HTTPException(status_code=400, detail="Path traversal attempt blocked.")
    
    # 2. Strict file whitelist: only allow valid package files
    allowed_files = {"manifest.json", "captions.vtt", "post_copy.txt"}
    if not (file_name in allowed_files or file_name.endswith(".mp4")):
        raise HTTPException(status_code=400, detail="Forbidden file access requested.")

    # 3. Project existence verification
    try:
        project = project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    # 4. Access Control: verify director credentials in production or when integration token configured
    if settings.app_env == "production" or settings.integration_service_token:
        expected_token = settings.integration_service_token
        is_authed = False
        if expected_token:
            if authorization == f"Bearer {expected_token}" or x_api_key == expected_token:
                is_authed = True
        elif settings.app_env != "production":
            is_authed = True

        if not is_authed:
            raise HTTPException(status_code=403, detail="Access denied: Valid Director authorization required to download export package.")

    # 5. Resolve and verify filesystem path containment
    plat_normalized = platform.lower().replace("platform.", "")
    if "tiktok" in plat_normalized:
        package_prefix = "tiktok"
    elif "instagram" in plat_normalized or "reels" in plat_normalized:
        package_prefix = "instagram"
    elif "youtube" in plat_normalized or "shorts" in plat_normalized:
        package_prefix = "youtube"
    else:
        package_prefix = plat_normalized

    base_dir = os.path.abspath(f"app/static/exports/{package_prefix}_{project_id}")
    target_file = os.path.abspath(os.path.join(base_dir, file_name))

    try:
        common = os.path.commonpath([base_dir, target_file])
    except ValueError:
        raise HTTPException(status_code=400, detail="Path traversal attempt blocked.")

    if common != base_dir or not os.path.exists(target_file):
        raise HTTPException(status_code=404, detail="Requested export file not found.")

    return FileResponse(target_file)




