from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, JSON, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.domain.project import (
    ContinuityProfile,
    Platform,
    PlatformExport,
    Project,
    ProjectInput,
    ProjectStatus,
    Scene,
    VideoPrompt,
)
from app.domain.facts import FactClaim, FactStatus
from app.domain.integration import ApprovalEvent, AuditEvent, ClipArtifact, ClipReviewEvent, DeliveryJob, EvidenceRecord, ExportManifest, FactVerificationJob, FinalReviewEvent, IdempotencyRecord, ProductionJob, YouTubeUploadJob
from app.services.project_service import ProjectNotFoundError


class Base(DeclarativeBase):
    pass


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    topic: Mapped[str] = mapped_column(String(500))
    duration_seconds: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(40))
    current_scene_number: Mapped[int] = mapped_column(default=0)
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    story_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    continuity_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    facts_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    scenes_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    prompts_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    prompt_history_data: Mapped[dict[str, list[dict[str, Any]]]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class IdempotencyRecordRow(Base):
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    operation: Mapped[str] = mapped_column(String(100))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_data: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class IntegrationEventRecord(Base):
    __tablename__ = "integration_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100))
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    metadata_data: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ApprovalEventRecord(Base):
    __tablename__ = "approval_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36))
    scene_number: Mapped[int] = mapped_column()
    decision: Mapped[str] = mapped_column(String(20))
    actor: Mapped[str] = mapped_column(String(120))
    comment: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class FactVerificationJobRecord(Base):
    __tablename__ = "fact_verification_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(30))
    claim_count: Mapped[int] = mapped_column()
    verified_count: Mapped[int] = mapped_column(default=0)
    failed_count: Mapped[int] = mapped_column(default=0)
    error: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class EvidenceRecordRow(Base):
    __tablename__ = "evidence_records"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36))
    claim_id: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(2000))
    normalized_url: Mapped[str] = mapped_column(String(2000))
    source_rank: Mapped[int] = mapped_column()
    notes: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ExportManifestRecord(Base):
    __tablename__ = "export_manifests"

    manifest_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36))
    package_version: Mapped[str] = mapped_column(String(50))
    checksum: Mapped[str] = mapped_column(String(64))
    markdown: Mapped[str] = mapped_column()
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DeliveryJobRecord(Base):
    __tablename__ = "delivery_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36))
    manifest_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30))
    attempts: Mapped[int] = mapped_column(default=0)
    error: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProductionJobRecord(Base):
    __tablename__ = "provider_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36))
    scene_number: Mapped[int] = mapped_column()
    prompt_version: Mapped[int] = mapped_column()
    job_type: Mapped[str] = mapped_column(String(30))
    provider: Mapped[str] = mapped_column(String(100))
    provider_job_id: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30))
    contract: Mapped[dict[str, Any]] = mapped_column(JSON)
    artifact_id: Mapped[str] = mapped_column(String(64), default="")
    error: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ClipArtifactRecord(Base):
    __tablename__ = "clip_artifacts"

    artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64))
    checksum: Mapped[str] = mapped_column(String(64))
    duration_seconds: Mapped[float] = mapped_column()
    aspect_ratio: Mapped[str] = mapped_column(String(20))
    narration_end_seconds: Mapped[float] = mapped_column()
    artifact_url: Mapped[str] = mapped_column(String(2000))
    review_status: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ClipReviewEventRecord(Base):
    __tablename__ = "clip_review_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36))
    scene_number: Mapped[int] = mapped_column()
    artifact_id: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(20))
    actor: Mapped[str] = mapped_column(String(200))
    comment: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class FinalReviewEventRecord(Base):
    __tablename__ = "final_review_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36))
    manifest_id: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(20))
    actor: Mapped[str] = mapped_column(String(200))
    comment: Mapped[str] = mapped_column(String(2000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class YouTubeUploadJobRecord(Base):
    __tablename__ = "youtube_upload_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36))
    manifest_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30))
    youtube_video_id: Mapped[str] = mapped_column(String(50), default="")
    upload_attempts: Mapped[int] = mapped_column(default=0)
    error_class: Mapped[str] = mapped_column(String(50), default="")
    upload_checksum: Mapped[str] = mapped_column(String(64))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    youtube_url: Mapped[str] = mapped_column(String(500), default="")
    error: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SqlProjectRepository:
    """PostgreSQL repository; nested MVP state is stored as versionable JSON."""

    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)

    def save(self, project: Project) -> Project:
        with Session(self.engine) as session:
            record = session.get(ProjectRecord, str(project.id))
            if record is None:
                record = ProjectRecord(id=str(project.id), topic=project.input.topic, duration_seconds=project.input.duration_seconds)
                session.add(record)
            record.topic = project.input.topic
            record.duration_seconds = project.input.duration_seconds
            record.status = project.status.value
            record.current_scene_number = project.current_scene_number
            exports_data = {}
            for k, v in getattr(project, "platform_exports", {}).items():
                exports_data[k] = {
                    "platform": v.platform.value if hasattr(v.platform, "value") else str(v.platform),
                    "aspect_ratio": v.aspect_ratio,
                    "output_asset_ref": v.output_asset_ref,
                    "export_status": v.export_status,
                    "publish_status": v.publish_status,
                    "publish_asset_ref": v.publish_asset_ref,
                    "publish_metadata": v.publish_metadata or {},
                }

            record.input_data = {
                "facts": project.input.facts,
                "source_urls": project.input.source_urls,
                "language": project.input.language,
                "tone": project.input.tone,
                "audience": project.input.audience,
                "visual_preferences": project.input.visual_preferences,
                "autonomous": project.input.autonomous,
                "tts_provider": project.input.tts_provider,
                "video_provider": project.input.video_provider,
                "stitch_provider": project.input.stitch_provider,
                "publish_provider": project.input.publish_provider,
                "token_budget": getattr(project.input, "token_budget", 50000),
                "target_platforms": [
                    p.value if hasattr(p, "value") else str(p)
                    for p in getattr(project.input, "target_platforms", [Platform.YOUTUBE_SHORTS])
                ],
                "model_tier": getattr(project.input, "model_tier", "flagship"),
                "platform_exports": exports_data,
            }

            record.story_data = {
                "hook": project.story_hook,
                "central_claim": project.story_central_claim,
                "ending": project.story_ending,
            }
            record.continuity_data = project.continuity.__dict__
            record.facts_data = [
                {"id": fact.id, "text": fact.text, "status": fact.status.value, "confidence": fact.confidence, "sources": fact.sources, "notes": fact.notes}
                for fact in project.facts
            ]
            record.scenes_data = [scene.__dict__ for scene in project.scenes]
            record.prompts_data = [
                {"scene_number": prompt.scene_number, "total_scenes": prompt.total_scenes, "text": prompt.text, "narration": prompt.narration, "narration_word_count": prompt.narration_word_count, "estimated_narration_seconds": prompt.estimated_narration_seconds, "beats": prompt.beats, "captions": prompt.captions, "continuity_lock": prompt.continuity_lock, "audio_plan": prompt.audio_plan, "final_requirements": prompt.final_requirements, "version_number": prompt.version_number, "template_version": prompt.template_version, "why_this_prompt": prompt.why_this_prompt, "quality_scores": prompt.quality_scores, "provider_name": prompt.provider_name, "model_name": prompt.model_name, "generation_latency_ms": prompt.generation_latency_ms, "repair_attempts": prompt.repair_attempts, "estimated_input_tokens": prompt.estimated_input_tokens, "estimated_output_tokens": prompt.estimated_output_tokens}
                for prompt in project.prompts.values()
            ]
            record.prompt_history_data = {
                str(scene_number): [
                    {"scene_number": prompt.scene_number, "total_scenes": prompt.total_scenes, "text": prompt.text, "narration": prompt.narration, "narration_word_count": prompt.narration_word_count, "estimated_narration_seconds": prompt.estimated_narration_seconds, "beats": prompt.beats, "captions": prompt.captions, "continuity_lock": prompt.continuity_lock, "audio_plan": prompt.audio_plan, "final_requirements": prompt.final_requirements, "version_number": prompt.version_number, "template_version": prompt.template_version, "why_this_prompt": prompt.why_this_prompt, "quality_scores": prompt.quality_scores, "provider_name": prompt.provider_name, "model_name": prompt.model_name, "generation_latency_ms": prompt.generation_latency_ms, "repair_attempts": prompt.repair_attempts, "estimated_input_tokens": prompt.estimated_input_tokens, "estimated_output_tokens": prompt.estimated_output_tokens}
                    for prompt in prompts
                ]
                for scene_number, prompts in project.prompt_history.items()
            }
            session.commit()
        return project

    def get(self, project_id: UUID) -> Project:
        with Session(self.engine) as session:
            record = session.get(ProjectRecord, str(project_id))
            if record is None:
                raise ProjectNotFoundError(str(project_id))
            return self._to_domain(record)

    def get_idempotency(self, key: str) -> IdempotencyRecord | None:
        with Session(self.engine) as session:
            record = session.get(IdempotencyRecordRow, key)
            if record is None:
                return None
            return IdempotencyRecord(record.key, record.operation, record.request_hash, record.response_data or {}, record.created_at)

    def save_idempotency(self, item: IdempotencyRecord) -> None:
        with Session(self.engine) as session:
            record = session.get(IdempotencyRecordRow, item.key)
            if record is None:
                record = IdempotencyRecordRow(key=item.key, operation=item.operation, request_hash=item.request_hash, response_data=item.response)
                session.add(record)
            else:
                record.operation = item.operation
                record.request_hash = item.request_hash
                record.response_data = item.response
            session.commit()

    def save_audit_event(self, event: AuditEvent) -> None:
        with Session(self.engine) as session:
            if session.get(IntegrationEventRecord, event.event_id) is None:
                session.add(IntegrationEventRecord(event_id=event.event_id, event_type=event.event_type, project_id=event.project_id, request_id=event.request_id, metadata_data=event.metadata))
                session.commit()

    def save_approval_event(self, event: ApprovalEvent) -> None:
        with Session(self.engine) as session:
            if session.get(ApprovalEventRecord, event.event_id) is None:
                session.add(ApprovalEventRecord(event_id=event.event_id, project_id=event.project_id, scene_number=event.scene_number, decision=event.decision, actor=event.actor, comment=event.comment))
                session.commit()

    def save_fact_job(self, job: FactVerificationJob) -> None:
        with Session(self.engine) as session:
            record = session.get(FactVerificationJobRecord, job.job_id)
            if record is None:
                record = FactVerificationJobRecord(job_id=job.job_id, project_id=job.project_id, status=job.status, claim_count=job.claim_count)
                session.add(record)
            record.status = job.status
            record.verified_count = job.verified_count
            record.failed_count = job.failed_count
            record.error = job.error
            record.updated_at = job.updated_at
            session.commit()

    def get_fact_job(self, job_id: str) -> FactVerificationJob | None:
        with Session(self.engine) as session:
            record = session.get(FactVerificationJobRecord, job_id)
            if record is None:
                return None
            return FactVerificationJob(record.job_id, record.project_id, record.status, record.claim_count, record.verified_count, record.failed_count, record.error, record.created_at, record.updated_at)

    def save_evidence(self, evidence: EvidenceRecord) -> None:
        with Session(self.engine) as session:
            if session.get(EvidenceRecordRow, evidence.evidence_id) is None:
                session.add(EvidenceRecordRow(evidence_id=evidence.evidence_id, project_id=evidence.project_id, claim_id=evidence.claim_id, url=evidence.url, normalized_url=evidence.normalized_url, source_rank=evidence.source_rank, notes=evidence.notes))
                session.commit()

    def save_export_manifest(self, manifest: ExportManifest) -> None:
        with Session(self.engine) as session:
            session.add(ExportManifestRecord(manifest_id=manifest.manifest_id, project_id=manifest.project_id, package_version=manifest.package_version, checksum=manifest.checksum, markdown=manifest.markdown, data=manifest.data, created_at=manifest.created_at, expires_at=manifest.expires_at))
            session.commit()

    def get_export_manifest(self, manifest_id: str) -> ExportManifest | None:
        with Session(self.engine) as session:
            record = session.get(ExportManifestRecord, manifest_id)
            if record is None:
                return None
            return ExportManifest(record.manifest_id, record.project_id, record.package_version, record.checksum, record.markdown, record.data or {}, record.created_at, record.expires_at)

    def save_delivery_job(self, job: DeliveryJob) -> None:
        with Session(self.engine) as session:
            session.add(DeliveryJobRecord(job_id=job.job_id, project_id=job.project_id, manifest_id=job.manifest_id, status=job.status, attempts=job.attempts, error=job.error, created_at=job.created_at, updated_at=job.updated_at))
            session.commit()

    def get_delivery_job(self, job_id: str) -> DeliveryJob | None:
        with Session(self.engine) as session:
            record = session.get(DeliveryJobRecord, job_id)
            if record is None:
                return None
            return DeliveryJob(record.job_id, record.project_id, record.manifest_id, record.status, record.attempts, record.error, record.created_at, record.updated_at)

    def save_production_job(self, job: ProductionJob) -> None:
        with Session(self.engine) as session:
            record = session.get(ProductionJobRecord, job.job_id)
            if record is None:
                record = ProductionJobRecord(job_id=job.job_id, project_id=job.project_id, scene_number=job.scene_number, prompt_version=job.prompt_version, job_type=job.job_type, provider=job.provider, provider_job_id=job.provider_job_id, status=job.status, contract=job.contract, created_at=job.created_at, updated_at=job.updated_at)
                session.add(record)
            record.status = job.status
            record.artifact_id = job.artifact_id
            record.error = job.error
            record.updated_at = job.updated_at
            session.commit()

    def get_production_job(self, job_id: str) -> ProductionJob | None:
        with Session(self.engine) as session:
            record = session.get(ProductionJobRecord, job_id)
            if record is None:
                return None
            return ProductionJob(record.job_id, record.project_id, record.scene_number, record.prompt_version, record.job_type, record.provider, record.provider_job_id, record.status, record.contract or {}, record.artifact_id, record.error, record.created_at, record.updated_at)

    def get_production_for_prompt(self, project_id: str, scene_number: int, prompt_version: int) -> ProductionJob | None:
        with Session(self.engine) as session:
            record = session.scalar(select(ProductionJobRecord).where(ProductionJobRecord.project_id == project_id, ProductionJobRecord.scene_number == scene_number, ProductionJobRecord.prompt_version == prompt_version))
            if record is None:
                return None
            return ProductionJob(record.job_id, record.project_id, record.scene_number, record.prompt_version, record.job_type, record.provider, record.provider_job_id, record.status, record.contract or {}, record.artifact_id, record.error, record.created_at, record.updated_at)

    def save_clip_artifact(self, artifact: ClipArtifact) -> None:
        with Session(self.engine) as session:
            record = session.get(ClipArtifactRecord, artifact.artifact_id)
            if record is None:
                session.add(ClipArtifactRecord(artifact_id=artifact.artifact_id, job_id=artifact.job_id, checksum=artifact.checksum, duration_seconds=artifact.duration_seconds, aspect_ratio=artifact.aspect_ratio, narration_end_seconds=artifact.narration_end_seconds, artifact_url=artifact.artifact_url, review_status=artifact.review_status, created_at=artifact.created_at))
            else:
                record.review_status = artifact.review_status
            session.commit()

    def get_clip_artifact(self, artifact_id: str) -> ClipArtifact | None:
        with Session(self.engine) as session:
            record = session.get(ClipArtifactRecord, artifact_id)
            if record is None:
                return None
            return ClipArtifact(record.artifact_id, record.job_id, record.checksum, record.duration_seconds, record.aspect_ratio, record.narration_end_seconds, record.artifact_url, record.review_status, record.created_at)

    def get_clip_artifacts_for_project(self, project_id: str) -> list[ClipArtifact]:
        with Session(self.engine) as session:
            from sqlalchemy import select as sa_select
            job_ids = [
                row.job_id
                for row in session.scalars(
                    sa_select(ProductionJobRecord.job_id).where(ProductionJobRecord.project_id == project_id)
                )
            ]
            records = session.scalars(
                sa_select(ClipArtifactRecord).where(ClipArtifactRecord.job_id.in_(job_ids))
            ).all()
            return [ClipArtifact(r.artifact_id, r.job_id, r.checksum, r.duration_seconds, r.aspect_ratio, r.narration_end_seconds, r.artifact_url, r.review_status, r.created_at) for r in records]

    def save_clip_review_event(self, event: ClipReviewEvent) -> None:
        with Session(self.engine) as session:
            if session.get(ClipReviewEventRecord, event.event_id) is None:
                session.add(ClipReviewEventRecord(event_id=event.event_id, project_id=event.project_id, scene_number=event.scene_number, artifact_id=event.artifact_id, decision=event.decision, actor=event.actor, comment=event.comment, created_at=event.created_at))
                session.commit()

    def save_final_review_event(self, event: FinalReviewEvent) -> None:
        with Session(self.engine) as session:
            if session.get(FinalReviewEventRecord, event.event_id) is None:
                session.add(FinalReviewEventRecord(event_id=event.event_id, project_id=event.project_id, manifest_id=event.manifest_id, decision=event.decision, actor=event.actor, comment=event.comment, created_at=event.created_at))
                session.commit()

    def get_latest_final_review(self, project_id: str) -> FinalReviewEvent | None:
        with Session(self.engine) as session:
            from sqlalchemy import select as sa_select
            record = session.scalar(
                sa_select(FinalReviewEventRecord)
                .where(FinalReviewEventRecord.project_id == project_id)
                .order_by(FinalReviewEventRecord.created_at.desc())
                .limit(1)
            )
            if record is None:
                return None
            return FinalReviewEvent(record.event_id, record.project_id, record.manifest_id, record.decision, record.actor, record.comment, record.created_at)

    def get_latest_export_manifest(self, project_id: str) -> ExportManifest | None:
        with Session(self.engine) as session:
            from sqlalchemy import select as sa_select
            record = session.scalar(
                sa_select(ExportManifestRecord)
                .where(ExportManifestRecord.project_id == project_id)
                .order_by(ExportManifestRecord.created_at.desc())
                .limit(1)
            )
            if record is None:
                return None
            return ExportManifest(record.manifest_id, record.project_id, record.package_version, record.checksum, record.markdown, record.data or {}, record.created_at, record.expires_at)

    def save_youtube_upload_job(self, job: YouTubeUploadJob) -> None:
        with Session(self.engine) as session:
            record = session.get(YouTubeUploadJobRecord, job.job_id)
            if record is None:
                record = YouTubeUploadJobRecord(job_id=job.job_id, project_id=job.project_id, manifest_id=job.manifest_id, status=job.status, upload_checksum=job.upload_checksum, created_at=job.created_at, updated_at=job.updated_at)
                session.add(record)
            record.status = job.status
            record.youtube_video_id = job.youtube_video_id
            record.upload_attempts = job.upload_attempts
            record.error_class = job.error_class
            record.youtube_url = job.youtube_url
            record.error = job.error
            record.published_at = job.published_at
            record.updated_at = job.updated_at
            session.commit()

    def get_youtube_upload_job(self, job_id: str) -> YouTubeUploadJob | None:
        with Session(self.engine) as session:
            record = session.get(YouTubeUploadJobRecord, job_id)
            if record is None:
                return None
            return YouTubeUploadJob(record.job_id, record.project_id, record.manifest_id, record.status, record.upload_checksum, record.youtube_video_id, record.upload_attempts, record.error_class, record.published_at, record.youtube_url, record.error, record.created_at, record.updated_at)

    def get_active_upload_job(self, project_id: str) -> YouTubeUploadJob | None:
        with Session(self.engine) as session:
            from sqlalchemy import select as sa_select
            record = session.scalar(
                sa_select(YouTubeUploadJobRecord)
                .where(YouTubeUploadJobRecord.project_id == project_id, YouTubeUploadJobRecord.status == "UPLOADING")
                .limit(1)
            )
            if record is None:
                return None
            return YouTubeUploadJob(record.job_id, record.project_id, record.manifest_id, record.status, record.upload_checksum, record.youtube_video_id, record.upload_attempts, record.error_class, record.published_at, record.youtube_url, record.error, record.created_at, record.updated_at)

    def get_approval_events_for_project(self, project_id: str) -> list:
        with Session(self.engine) as session:
            from sqlalchemy import select as sa_select
            from app.domain.integration import ApprovalEvent as AE
            records = session.scalars(
                sa_select(ApprovalEventRecord).where(ApprovalEventRecord.project_id == project_id)
            ).all()
            return [AE(r.event_id, r.project_id, r.scene_number, r.decision, r.actor, r.comment, r.created_at) for r in records]

    @staticmethod
    def _to_domain(record: ProjectRecord) -> Project:
        input_data = dict(record.input_data or {})
        platform_exports_raw = input_data.pop("platform_exports", {})
        if "target_platforms" in input_data:
            input_data["target_platforms"] = [
                Platform(p) if isinstance(p, str) else p
                for p in input_data["target_platforms"]
            ]
        project = Project(
            id=UUID(record.id),
            status=ProjectStatus(record.status),
            current_scene_number=record.current_scene_number,
            input=ProjectInput(topic=record.topic, duration_seconds=record.duration_seconds, **input_data),
        )
        for k, v in (platform_exports_raw or {}).items():
            project.platform_exports[k] = PlatformExport(
                platform=Platform(v["platform"]) if isinstance(v["platform"], str) else v["platform"],
                aspect_ratio=v.get("aspect_ratio", "9:16"),
                output_asset_ref=v.get("output_asset_ref", ""),
                export_status=v.get("export_status", "COMPLETED"),
                publish_status=v.get("publish_status", "NOT_STARTED"),
                publish_asset_ref=v.get("publish_asset_ref"),
                publish_metadata=v.get("publish_metadata", {}),
            )
        story = record.story_data or {}
        project.story_hook = story.get("hook", "")
        project.story_central_claim = story.get("central_claim", "")
        project.story_ending = story.get("ending", "")
        project.continuity = ContinuityProfile(**(record.continuity_data or {}))
        project.facts = [
            FactClaim(id=item["id"], text=item["text"], status=FactStatus(item["status"]), confidence=item.get("confidence", 0.0), sources=item.get("sources", []), notes=item.get("notes", ""))
            for item in (record.facts_data or [])
        ]
        project.scenes = [Scene(**scene) for scene in (record.scenes_data or [])]
        project.prompts = {
            item["scene_number"]: VideoPrompt(project_id=project.id, **item)
            for item in (record.prompts_data or [])
        }
        project.prompt_history = {
            int(scene_number): [
                VideoPrompt(project_id=project.id, **item)
                for item in prompts
            ]
            for scene_number, prompts in (record.prompt_history_data or {}).items()
        }
        return project
