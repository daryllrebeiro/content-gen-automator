from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class IdempotencyRecord:
    key: str
    operation: str
    request_hash: str
    response: dict[str, Any]
    created_at: datetime


@dataclass
class AuditEvent:
    event_id: str
    event_type: str
    project_id: str | None
    request_id: str | None
    metadata: dict[str, Any]
    created_at: datetime

    @classmethod
    def now(cls, event_id: str, event_type: str, project_id: str | None = None, request_id: str | None = None, metadata: dict[str, Any] | None = None) -> "AuditEvent":
        return cls(event_id, event_type, project_id, request_id, metadata or {}, datetime.now(timezone.utc))


@dataclass
class ApprovalEvent:
    event_id: str
    project_id: str
    scene_number: int
    decision: str
    actor: str
    comment: str
    created_at: datetime


@dataclass
class FactVerificationJob:
    job_id: str
    project_id: str
    status: str
    claim_count: int
    verified_count: int = 0
    failed_count: int = 0
    error: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EvidenceRecord:
    evidence_id: str
    project_id: str
    claim_id: str
    url: str
    normalized_url: str
    source_rank: int
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExportManifest:
    manifest_id: str
    project_id: str
    package_version: str
    checksum: str
    markdown: str
    data: dict[str, Any]
    created_at: datetime
    expires_at: datetime


@dataclass
class DeliveryJob:
    job_id: str
    project_id: str
    manifest_id: str
    status: str
    attempts: int = 0
    error: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ProductionJob:
    job_id: str
    project_id: str
    scene_number: int
    prompt_version: int
    job_type: str
    provider: str
    provider_job_id: str
    status: str
    contract: dict[str, Any]
    artifact_id: str = ""
    error: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ClipArtifact:
    artifact_id: str
    job_id: str
    checksum: str
    duration_seconds: float
    aspect_ratio: str
    narration_end_seconds: float
    artifact_url: str
    review_status: str = "VIDEO_REVIEW_PENDING"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ClipReviewEvent:
    event_id: str
    project_id: str
    scene_number: int
    artifact_id: str
    decision: str
    actor: str
    comment: str
    created_at: datetime


@dataclass
class FinalReviewEvent:
    event_id: str
    project_id: str
    manifest_id: str
    decision: str
    actor: str
    comment: str
    created_at: datetime


@dataclass
class YouTubeUploadJob:
    job_id: str
    project_id: str
    manifest_id: str
    status: str
    upload_checksum: str
    youtube_video_id: str = ""
    upload_attempts: int = 0
    error_class: str = ""
    published_at: datetime | None = None
    youtube_url: str = ""
    error: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
