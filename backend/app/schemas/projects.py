from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


DurationSeconds = Literal[10, 20, 30]


class ProjectCreateRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    facts: list[str] = Field(default_factory=list, max_length=20)
    source_urls: list[str] = Field(default_factory=list, max_length=20)
    language: str = Field(default="English", min_length=2, max_length=50)
    tone: str = Field(default="curious cinematic documentary", max_length=100)
    audience: str = Field(default="general audience", max_length=100)
    visual_preferences: dict[str, str] = Field(default_factory=dict)
    duration_seconds: DurationSeconds = 30
    autonomous: bool = Field(default=False)
    tts_provider: str = Field(default="mock")
    video_provider: str = Field(default="mock")
    stitch_provider: str = Field(default="mock")
    publish_provider: str = Field(default="mock")
    token_budget: int = Field(default=50000, description="Max token cost ceiling for Auto-Pilot runs")




class SceneResponse(BaseModel):
    number: int
    purpose: str
    summary: str
    previous_scene_number: int | None


class PromptResponse(BaseModel):
    scene_number: int
    total_scenes: int
    duration_seconds: int = 10
    text: str
    narration: str
    narration_word_count: int
    estimated_narration_seconds: float
    version_number: int = 1
    template_version: str = "prompt_composer_v1"
    why_this_prompt: list[str] = []
    quality_scores: dict[str, float] = {}
    provider_name: str = "mock"
    model_name: str = "mock-v1"
    generation_latency_ms: float = 0.0
    repair_attempts: int = 0
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0


class FactResponse(BaseModel):
    id: str
    text: str
    status: str
    confidence: float
    sources: list[str]
    notes: str
    approved_for_narration: bool


class ProjectResponse(BaseModel):
    id: UUID
    status: str
    topic: str
    duration_seconds: int
    current_scene_number: int
    total_scenes: int
    story_hook: str
    story_central_claim: str
    story_ending: str
    facts: list[FactResponse]
    scenes: list[SceneResponse]
    continuity: dict
    prompts: list[PromptResponse]
    tts_provider: str
    video_provider: str
    stitch_provider: str
    publish_provider: str



class PublishingResponse(BaseModel):
    title: str
    description: str
    hashtags: list[str]
    pinned_comment: str


class ExportResponse(BaseModel):
    project_id: UUID
    markdown: str
    publishing: PublishingResponse
    data: dict


class IntegrationProjectResponse(BaseModel):
    project_id: UUID
    created: bool
    status: str
    total_scenes: int


class IntegrationStatusResponse(BaseModel):
    project_id: UUID
    status: str
    current_scene_number: int
    total_scenes: int
    next_scene_number: int | None


class IntegrationPromptResponse(BaseModel):
    project_id: UUID
    prompt: PromptResponse
    status: str


class ApprovalRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=120)
    comment: str = Field(default="", max_length=1000)


class ApprovalResponse(BaseModel):
    project_id: UUID
    scene_number: int
    decision: str
    status: str


class FactVerificationResponse(BaseModel):
    job_id: str
    project_id: UUID
    status: str
    claim_count: int
    verified_count: int
    failed_count: int
    error: str = ""


class ExportManifestResponse(BaseModel):
    manifest_id: str
    project_id: UUID
    package_version: str
    checksum: str
    expires_at: str
    download_token: str


class DeliveryJobResponse(BaseModel):
    job_id: str
    project_id: UUID
    manifest_id: str
    status: str
    attempts: int
    error: str = ""


class ProductionJobResponse(BaseModel):
    job_id: str
    project_id: UUID
    scene_number: int
    prompt_version: int
    job_type: str
    provider: str
    provider_job_id: str
    status: str
    contract: dict
    artifact_id: str = ""
    error: str = ""


# ---------------------------------------------------------------------------
# Phase 8 — Publishing automation schemas
# ---------------------------------------------------------------------------

class ClipReviewRequest(BaseModel):
    artifact_id: str = Field(min_length=1, max_length=64)
    decision: Literal["approved", "rejected"]
    actor: str = Field(min_length=1, max_length=200)
    comment: str = Field(default="", max_length=1000)


class ClipReviewResponse(BaseModel):
    project_id: UUID
    scene_number: int
    artifact_id: str
    decision: str
    actor: str
    status: str  # clip review_status after decision


class FinalReviewRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=200)
    manifest_id: str = Field(min_length=1, max_length=64)
    comment: str = Field(default="", max_length=2000)


class FinalReviewResponse(BaseModel):
    project_id: UUID
    decision: str
    actor: str
    manifest_id: str
    project_status: str


class FinalReviewStatusResponse(BaseModel):
    project_id: UUID
    has_review: bool
    decision: str | None
    actor: str | None
    manifest_id: str | None
    comment: str | None


class GateReportResponse(BaseModel):
    can_publish: bool
    failed_gates: list[str]


class PublishRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=1, max_length=200)


class PublishResponse(BaseModel):
    job_id: str
    project_id: UUID
    manifest_id: str
    status: str
    upload_checksum: str


class YouTubeUploadJobResponse(BaseModel):
    job_id: str
    project_id: UUID
    manifest_id: str
    status: str
    youtube_video_id: str = ""
    upload_attempts: int
    error_class: str = ""
    youtube_url: str = ""
    error: str = ""


class MetadataValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]
