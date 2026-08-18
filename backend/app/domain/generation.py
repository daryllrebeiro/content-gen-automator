from dataclasses import dataclass, field

from app.domain.project import Project, Scene
from app.policies.contract import NARRATION_CUTOFF_SECONDS, SAFETY_POLICY_VERSION, VOICE_LOCK_ID


@dataclass
class NarrationDraft:
    text: str
    word_count: int
    estimated_seconds: float


@dataclass
class VisualDirection:
    story_action: str
    camera: str
    composition: str
    transition: str
    beats: list[dict[str, object]] = field(default_factory=list)


@dataclass
class ProductionContract:
    duration_seconds: int = 10
    aspect_ratio: str = "9:16"
    narration_max_seconds: float = NARRATION_CUTOFF_SECONDS
    animation_only: bool = True
    voice_id: str = VOICE_LOCK_ID
    safety_policy_version: str = SAFETY_POLICY_VERSION


@dataclass
class PromptSections:
    continuity_lock: list[str] = field(default_factory=list)
    captions: list[str] = field(default_factory=list)
    audio_plan: list[str] = field(default_factory=list)
    final_requirements: list[str] = field(default_factory=list)


@dataclass
class GenerationContext:
    project: Project
    scene: Scene
    contract: ProductionContract = field(default_factory=ProductionContract)
