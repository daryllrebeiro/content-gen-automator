from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from app.domain.generation import ProductionContract
from app.domain.integration import ClipArtifact, ProductionJob
from app.domain.project import Project


class ProductionService:
    def submit_clip(self, project: Project, scene_number: int, repository) -> ProductionJob:
        prompt = project.prompts.get(scene_number)
        if prompt is None:
            raise ValueError("Generate the prompt before submitting production.")
        existing = getattr(repository, "get_production_for_prompt", lambda *_: None)(str(project.id), scene_number, prompt.version_number)
        if existing is not None:
            return existing
        contract = ProductionContract()
        job = ProductionJob(str(uuid4()), str(project.id), scene_number, prompt.version_number, "video_clip", "mock-video-provider", f"mock-{uuid4()}", "SUBMITTED", {"duration_seconds": contract.duration_seconds, "aspect_ratio": contract.aspect_ratio, "narration_max_seconds": contract.narration_max_seconds, "animation_only": contract.animation_only, "voice_id": contract.voice_id, "safety_policy_version": contract.safety_policy_version})
        if hasattr(repository, "save_production_job"):
            repository.save_production_job(job)
        return job

    def complete_callback(self, job: ProductionJob, payload: dict[str, object], repository) -> ProductionJob:
        if job.status in {"SUCCEEDED", "FAILED_PERMANENT"}:
            return job
        status = str(payload.get("status", "")).upper()
        if status not in {"SUCCEEDED", "FAILED_RETRYABLE", "FAILED_PERMANENT"}:
            raise ValueError("Unsupported provider callback status.")
        if status == "SUCCEEDED":
            duration = float(payload.get("duration_seconds", 0))
            aspect_ratio = str(payload.get("aspect_ratio", ""))
            narration_end = float(payload.get("narration_end_seconds", 99))
            if duration != 10 or aspect_ratio != "9:16" or narration_end >= 9:
                job.status = "FAILED_PERMANENT"
                job.error = "Artifact failed the production contract: expected 10 seconds, 9:16, and narration before 9 seconds."
            else:
                artifact_id = str(uuid4())
                artifact = ClipArtifact(artifact_id, job.job_id, str(payload.get("checksum", "")), duration, aspect_ratio, narration_end, str(payload.get("artifact_url", "")))
                job.artifact_id = artifact_id
                if hasattr(repository, "save_clip_artifact"):
                    repository.save_clip_artifact(artifact)
                job.status = "SUCCEEDED"
        else:
            job.status = status
            job.error = str(payload.get("error", ""))
        job.updated_at = datetime.now(timezone.utc)
        if hasattr(repository, "save_production_job"):
            repository.save_production_job(job)
        return job
