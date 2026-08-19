from dataclasses import dataclass, field
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from app.domain.facts import FactClaim
from app.policies.contract import PROMPT_TEMPLATE_VERSION, scene_count_for_duration


DurationSeconds = Literal[10, 20, 30]


class ProjectStatus(str, Enum):
    CREATED = "CREATED"
    INPUT_RECEIVED = "INPUT_RECEIVED"
    FACT_CHECKING = "FACT_CHECKING"
    STORY_CREATED = "STORY_CREATED"
    SCENES_PLANNED = "SCENES_PLANNED"
    AWAITING_NEXT = "AWAITING_NEXT"
    PROMPT_APPROVAL_PENDING = "PROMPT_APPROVAL_PENDING"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    VIDEO_REVIEW_PENDING = "VIDEO_REVIEW_PENDING"
    VIDEO_APPROVED = "VIDEO_APPROVED"
    VIDEO_REJECTED = "VIDEO_REJECTED"
    PUBLISHING_PENDING = "PUBLISHING_PENDING"
    PUBLISHED = "PUBLISHED"
    PUBLISH_FAILED = "PUBLISH_FAILED"
    FAILED = "FAILED"


def scene_count(duration_seconds: DurationSeconds) -> int:
    return scene_count_for_duration(duration_seconds)


@dataclass
class ProjectInput:
    topic: str
    facts: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    language: str = "English"
    tone: str = "curious cinematic documentary"
    audience: str = "general audience"
    visual_preferences: dict[str, str] = field(default_factory=dict)
    duration_seconds: DurationSeconds = 30
    autonomous: bool = False



@dataclass
class Scene:
    number: int
    purpose: str
    summary: str
    previous_scene_number: int | None = None


@dataclass
class ContinuityProfile:
    animation_style: str = "stylized cinematic 3D animation"
    palette: str = "warm amber, deep blue, and muted brown"
    camera_language: str = "smooth animated documentary camera"
    voice_id: str = "documentary_voice_01"
    voice_description: str = (
        "warm, calm, trustworthy neutral-English documentary narrator; medium-low pitch"
    )
    characters: list[str] = field(default_factory=list)
    continuity_rules: list[str] = field(default_factory=list)


@dataclass
class VideoPrompt:
    project_id: UUID
    scene_number: int
    total_scenes: int
    text: str
    narration: str
    narration_word_count: int
    estimated_narration_seconds: float
    beats: list[dict[str, object]] = field(default_factory=list)
    captions: list[str] = field(default_factory=list)
    continuity_lock: list[str] = field(default_factory=list)
    audio_plan: list[str] = field(default_factory=list)
    final_requirements: list[str] = field(default_factory=list)
    version_number: int = 1
    template_version: str = PROMPT_TEMPLATE_VERSION
    why_this_prompt: list[str] = field(default_factory=list)
    quality_scores: dict[str, float] = field(default_factory=dict)
    provider_name: str = "mock"
    model_name: str = "mock-v1"
    generation_latency_ms: float = 0.0
    repair_attempts: int = 0
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0


@dataclass
class Project:
    input: ProjectInput
    id: UUID = field(default_factory=uuid4)
    status: ProjectStatus = ProjectStatus.CREATED
    current_scene_number: int = 0
    story_hook: str = ""
    story_central_claim: str = ""
    story_ending: str = ""
    scenes: list[Scene] = field(default_factory=list)
    continuity: ContinuityProfile = field(default_factory=ContinuityProfile)
    facts: list[FactClaim] = field(default_factory=list)
    prompts: dict[int, VideoPrompt] = field(default_factory=dict)
    prompt_history: dict[int, list[VideoPrompt]] = field(default_factory=dict)
