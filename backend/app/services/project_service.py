from uuid import UUID
import os
import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from app.domain.integration import ApprovalEvent, AuditEvent, ClipArtifact, ClipReviewEvent, DeliveryJob, EvidenceRecord, ExportManifest, FactVerificationJob, FinalReviewEvent, IdempotencyRecord, ProductionJob, YouTubeUploadJob
from app.domain.facts import FactStatus

from app.domain.project import Project, ProjectInput, ProjectStatus, VideoPrompt
from app.services.prompt_pipeline import PromptGenerationPipeline, StoryArchitect
from app.services.fact_engine import FactEngine


class ProjectNotFoundError(LookupError):
    pass


class ProjectStateError(ValueError):
    pass


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self._projects: dict[UUID, Project] = {}
        self._idempotency: dict[str, IdempotencyRecord] = {}
        self.audit_events: list[AuditEvent] = []
        self.approval_events: list[ApprovalEvent] = []
        self.fact_jobs: dict[str, FactVerificationJob] = {}
        self.evidence_records: list[EvidenceRecord] = []
        self.export_manifests: dict[str, ExportManifest] = {}
        self.delivery_jobs: dict[str, DeliveryJob] = {}
        self.production_jobs: dict[str, ProductionJob] = {}
        self.clip_artifacts: dict[str, ClipArtifact] = {}
        self.clip_review_events: list[ClipReviewEvent] = []
        self.final_review_events: list[FinalReviewEvent] = []
        self.youtube_upload_jobs: dict[str, YouTubeUploadJob] = {}

    def save(self, project: Project) -> Project:
        self._projects[project.id] = project
        return project

    def get(self, project_id: UUID) -> Project:
        try:
            return self._projects[project_id]
        except KeyError as exc:
            raise ProjectNotFoundError(str(project_id)) from exc

    def get_idempotency(self, key: str) -> IdempotencyRecord | None:
        return self._idempotency.get(key)

    def save_idempotency(self, record: IdempotencyRecord) -> None:
        self._idempotency[record.key] = record

    def save_audit_event(self, event: AuditEvent) -> None:
        self.audit_events.append(event)

    def save_approval_event(self, event: ApprovalEvent) -> None:
        self.approval_events.append(event)

    def save_fact_job(self, job: FactVerificationJob) -> None:
        self.fact_jobs[job.job_id] = job

    def get_fact_job(self, job_id: str) -> FactVerificationJob | None:
        return self.fact_jobs.get(job_id)

    def save_evidence(self, evidence: EvidenceRecord) -> None:
        self.evidence_records.append(evidence)

    def save_export_manifest(self, manifest: ExportManifest) -> None:
        self.export_manifests[manifest.manifest_id] = manifest

    def get_export_manifest(self, manifest_id: str) -> ExportManifest | None:
        return self.export_manifests.get(manifest_id)

    def save_delivery_job(self, job: DeliveryJob) -> None:
        self.delivery_jobs[job.job_id] = job

    def get_delivery_job(self, job_id: str) -> DeliveryJob | None:
        return self.delivery_jobs.get(job_id)

    def save_production_job(self, job: ProductionJob) -> None:
        self.production_jobs[job.job_id] = job

    def get_production_job(self, job_id: str) -> ProductionJob | None:
        return self.production_jobs.get(job_id)

    def get_production_for_prompt(self, project_id: str, scene_number: int, prompt_version: int) -> ProductionJob | None:
        return next((job for job in self.production_jobs.values() if job.project_id == project_id and job.scene_number == scene_number and job.prompt_version == prompt_version), None)

    def save_clip_artifact(self, artifact: ClipArtifact) -> None:
        self.clip_artifacts[artifact.artifact_id] = artifact

    def get_clip_artifact(self, artifact_id: str) -> ClipArtifact | None:
        return self.clip_artifacts.get(artifact_id)

    def get_clip_artifacts_for_project(self, project_id: str) -> list[ClipArtifact]:
        job_ids = {job.job_id for job in self.production_jobs.values() if job.project_id == project_id}
        return [a for a in self.clip_artifacts.values() if a.job_id in job_ids]

    def save_clip_review_event(self, event: ClipReviewEvent) -> None:
        self.clip_review_events.append(event)

    def save_final_review_event(self, event: FinalReviewEvent) -> None:
        self.final_review_events.append(event)

    def get_latest_final_review(self, project_id: str) -> FinalReviewEvent | None:
        reviews = [ev for ev in self.final_review_events if ev.project_id == project_id]
        return reviews[-1] if reviews else None

    def get_latest_export_manifest(self, project_id: str) -> ExportManifest | None:
        manifests = [m for m in self.export_manifests.values() if m.project_id == project_id]
        return max(manifests, key=lambda m: m.created_at, default=None)

    def save_youtube_upload_job(self, job: YouTubeUploadJob) -> None:
        self.youtube_upload_jobs[job.job_id] = job

    def get_youtube_upload_job(self, job_id: str) -> YouTubeUploadJob | None:
        return self.youtube_upload_jobs.get(job_id)

    def get_active_upload_job(self, project_id: str) -> YouTubeUploadJob | None:
        return next(
            (j for j in self.youtube_upload_jobs.values() if j.project_id == project_id and j.status == "UPLOADING"),
            None,
        )

    def get_approval_events_for_project(self, project_id: str) -> list:
        return [ev for ev in self.approval_events if ev.project_id == project_id]


class ProjectService:
    def __init__(self, repository: InMemoryProjectRepository | None = None) -> None:
        self.repository = repository or self._default_repository()
        provider = self._default_provider()
        self.fact_engine = FactEngine(checker=provider if hasattr(provider, "verify_claim") else None)
        self.story_architect = StoryArchitect(provider)
        self.prompt_pipeline = PromptGenerationPipeline(provider)

    @staticmethod
    def _default_repository():
        if os.getenv("PROJECT_REPOSITORY", "memory").lower() != "postgres":
            return InMemoryProjectRepository()
        from app.repositories.sql import SqlProjectRepository

        return SqlProjectRepository(os.environ["DATABASE_URL"])

    @staticmethod
    def _default_provider():
        if os.getenv("LLM_PROVIDER", "mock").lower() != "gemini":
            from app.providers.mock import MockProvider

            return MockProvider()
        from app.providers.gemini import GeminiProvider
        from app.providers.reliability import RetryingProvider

        return RetryingProvider(
            GeminiProvider(),
            max_attempts=int(os.getenv("PROVIDER_MAX_ATTEMPTS", "3")),
            timeout_seconds=float(os.getenv("PROVIDER_TIMEOUT_SECONDS", "30")),
        )

    def create(self, project_input: ProjectInput) -> Project:
        project = Project(input=project_input, status=ProjectStatus.INPUT_RECEIVED)
        self.fact_engine.ingest(project)
        self.story_architect.create(project)
        project.status = ProjectStatus.SCENES_PLANNED
        self.repository.save(project)
        self._audit("project.created", str(project.id), metadata={"duration_seconds": project.input.duration_seconds})
        return project

    def create_idempotent(self, key: str, request_hash: str, project_input: ProjectInput) -> tuple[Project, bool]:
        existing = getattr(self.repository, "get_idempotency", lambda _: None)(key)
        if existing is not None:
            if existing.operation != "integration.projects.create" or existing.request_hash != request_hash:
                raise ProjectStateError("Idempotency key was reused with a different request payload.")
            return self.repository.get(UUID(existing.response["project_id"])), True
        project = self.create(project_input)
        record = IdempotencyRecord(
            key=key,
            operation="integration.projects.create",
            request_hash=request_hash,
            response={"project_id": str(project.id)},
            created_at=datetime.now(timezone.utc),
        )
        if hasattr(self.repository, "save_idempotency"):
            self.repository.save_idempotency(record)
        return project, False

    def _audit(self, event_type: str, project_id: str | None, request_id: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        if hasattr(self.repository, "save_audit_event"):
            event = AuditEvent.now(hashlib.sha256(f"{event_type}:{project_id}:{datetime.now(timezone.utc).timestamp()}".encode()).hexdigest()[:24], event_type, project_id, request_id, metadata)
            self.repository.save_audit_event(event)

    def generate_next(self, project_id: UUID, gemini_api_key: str | None = None) -> VideoPrompt:
        project = self.repository.get(project_id)
        next_number = project.current_scene_number + 1
        if next_number > len(project.scenes):
            if project.scenes and project.scenes[-1].number in project.prompts:
                return project.prompts[project.scenes[-1].number]
            raise ProjectStateError("All prompts have already been generated.")
        if project.current_scene_number > 0 and project.status != ProjectStatus.APPROVED:
            raise ProjectStateError("The current prompt must be approved before generating the next scene.")

        existing = project.prompts.get(next_number)
        if existing is not None:
            return existing

        if gemini_api_key:
            from app.providers.gemini import GeminiProvider
            from app.providers.reliability import RetryingProvider
            pipeline = PromptGenerationPipeline(
                RetryingProvider(
                    GeminiProvider(api_key=gemini_api_key),
                    max_attempts=int(os.getenv("PROVIDER_MAX_ATTEMPTS", "3")),
                    timeout_seconds=float(os.getenv("PROVIDER_TIMEOUT_SECONDS", "30")),
                )
            )
            prompt = pipeline.generate(project, project.scenes[next_number - 1])
        else:
            prompt = self.prompt_pipeline.generate(project, project.scenes[next_number - 1])

        project.prompts[next_number] = prompt
        project.current_scene_number = next_number
        project.status = (
            ProjectStatus.PROMPT_APPROVAL_PENDING
        )
        self.repository.save(project)
        self._audit("prompt.generated", str(project.id), metadata={"scene_number": next_number, "version": prompt.version_number})
        return prompt

    def decide_prompt(self, project_id: UUID, scene_number: int, *, decision: str, actor: str, comment: str) -> Project:
        project = self.repository.get(project_id)
        if scene_number not in project.prompts:
            raise ProjectStateError("Generate the prompt before requesting approval.")
        if scene_number != project.current_scene_number:
            raise ProjectStateError("Only the current prompt can be approved or rejected.")
        if decision not in {"approved", "rejected"}:
            raise ProjectStateError("Decision must be approved or rejected.")
        if decision == "approved":
            project.status = ProjectStatus.COMPLETED if scene_number == len(project.scenes) else ProjectStatus.APPROVED
        else:
            project.status = ProjectStatus.PROMPT_APPROVAL_PENDING
        self.repository.save(project)
        event_id = hashlib.sha256(f"{project.id}:{scene_number}:{decision}:{actor}:{datetime.now(timezone.utc).timestamp()}".encode()).hexdigest()[:24]
        event = ApprovalEvent(event_id, str(project.id), scene_number, decision, actor, comment, datetime.now(timezone.utc))
        if hasattr(self.repository, "save_approval_event"):
            self.repository.save_approval_event(event)
        self._audit(f"prompt.{decision}", str(project.id), metadata={"scene_number": scene_number, "actor": actor, "comment": comment})
        return project

    def verify_facts(self, project_id: UUID, job_id: str) -> FactVerificationJob:
        project = self.repository.get(project_id)
        job = FactVerificationJob(job_id=job_id, project_id=str(project_id), status="RUNNING", claim_count=len(project.facts))
        if hasattr(self.repository, "save_fact_job"):
            self.repository.save_fact_job(job)
        checker = self.fact_engine.checker
        if checker is None:
            job.status = "FAILED_RETRYABLE"
            job.error = "No evidence provider is configured."
            job.updated_at = datetime.now(timezone.utc)
            if hasattr(self.repository, "save_fact_job"):
                self.repository.save_fact_job(job)
            self._audit("facts.verification_failed", str(project.id), metadata={"job_id": job_id, "retryable": True})
            return job
        for claim in project.facts:
            try:
                verified = checker.verify_claim(claim, project.input.source_urls)
                if verified.status == FactStatus.VERIFIED and not verified.sources:
                    verified.status = FactStatus.UNCERTAIN
                    verified.notes = "Provider marked the claim verified without a source reference."
                claim.status = verified.status
                claim.confidence = verified.confidence
                claim.sources = verified.sources
                claim.notes = verified.notes
                if claim.status.value == "verified":
                    job.verified_count += 1
                elif claim.status.value in {"contradicted", "uncertain"}:
                    job.failed_count += 1
                for source in verified.sources:
                    normalized = source.strip().rstrip("/")
                    if normalized.startswith(("http://", "https://")) and hasattr(self.repository, "save_evidence"):
                        rank = 1 if any(domain in normalized.lower() for domain in (".gov", ".edu", ".org")) else 2
                        evidence_id = hashlib.sha256(f"{project.id}:{claim.id}:{normalized}".encode()).hexdigest()[:24]
                        self.repository.save_evidence(EvidenceRecord(evidence_id, str(project.id), claim.id, source, normalized, rank))
            except Exception as exc:
                claim.status = FactStatus.UNCERTAIN
                claim.notes = f"Evidence check failed: {exc}"
                job.failed_count += 1
        self.repository.save(project)
        job.status = "COMPLETED"
        job.updated_at = datetime.now(timezone.utc)
        if hasattr(self.repository, "save_fact_job"):
            self.repository.save_fact_job(job)
        self._audit("facts.verification_completed", str(project.id), metadata={"job_id": job_id, "verified_count": job.verified_count, "failed_count": job.failed_count})
        return job

    def regenerate(self, project_id: UUID, scene_number: int, gemini_api_key: str | None = None) -> VideoPrompt:
        project = self.repository.get(project_id)
        if scene_number < 1 or scene_number > len(project.scenes):
            raise ProjectStateError("Scene number is outside this project.")
        if scene_number not in project.prompts:
            raise ProjectStateError("Generate the scene once before regenerating it.")

        current = project.prompts[scene_number]
        history = project.prompt_history.setdefault(scene_number, [])
        history.append(current)

        if gemini_api_key:
            from app.providers.gemini import GeminiProvider
            from app.providers.reliability import RetryingProvider
            pipeline = PromptGenerationPipeline(
                RetryingProvider(
                    GeminiProvider(api_key=gemini_api_key),
                    max_attempts=int(os.getenv("PROVIDER_MAX_ATTEMPTS", "3")),
                    timeout_seconds=float(os.getenv("PROVIDER_TIMEOUT_SECONDS", "30")),
                )
            )
            regenerated = pipeline.generate(project, project.scenes[scene_number - 1])
        else:
            regenerated = self.prompt_pipeline.generate(project, project.scenes[scene_number - 1])

        regenerated.version_number = current.version_number + 1
        regenerated.template_version = current.template_version
        project.prompts[scene_number] = regenerated
        self.repository.save(project)
        self._audit("prompt.regenerated", str(project.id), metadata={"scene_number": scene_number, "version": regenerated.version_number})
        return regenerated
