from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, JSON, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.domain.project import (
    ContinuityProfile,
    Project,
    ProjectInput,
    ProjectStatus,
    Scene,
    VideoPrompt,
)
from app.domain.facts import FactClaim, FactStatus
from app.domain.integration import ApprovalEvent, AuditEvent, EvidenceRecord, FactVerificationJob, IdempotencyRecord
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
            record.input_data = {
                "facts": project.input.facts,
                "source_urls": project.input.source_urls,
                "language": project.input.language,
                "tone": project.input.tone,
                "audience": project.input.audience,
                "visual_preferences": project.input.visual_preferences,
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

    @staticmethod
    def _to_domain(record: ProjectRecord) -> Project:
        input_data = record.input_data or {}
        project = Project(
            id=UUID(record.id),
            status=ProjectStatus(record.status),
            current_scene_number=record.current_scene_number,
            input=ProjectInput(topic=record.topic, duration_seconds=record.duration_seconds, **input_data),
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
