from dataclasses import dataclass, field

from app.domain.project import Project, Scene


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
    narration_max_seconds: float = 9.0
    animation_only: bool = True
    voice_id: str = "documentary_voice_01"
    safety_policy_version: str = "global_video_policy_v1"


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
