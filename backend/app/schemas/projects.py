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
