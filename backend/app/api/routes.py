from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.schemas.health import HealthResponse
from app.schemas.projects import (
    FactResponse,
    ExportResponse,
    ProjectCreateRequest,
    ProjectResponse,
    PromptResponse,
    PublishingResponse,
    SceneResponse,
)
from app.domain.project import ProjectInput
from app.services.project_service import (
    ProjectNotFoundError,
    ProjectService,
    ProjectStateError,
)
from app.services.export_service import ExportService


router = APIRouter()
project_service = ProjectService()
export_service = ExportService()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="shorts-prompt-agent")


def _prompt_response(prompt) -> PromptResponse:
    return PromptResponse(
        scene_number=prompt.scene_number,
        total_scenes=prompt.total_scenes,
        text=prompt.text,
        narration=prompt.narration,
        narration_word_count=prompt.narration_word_count,
        estimated_narration_seconds=prompt.estimated_narration_seconds,
        version_number=prompt.version_number,
        template_version=prompt.template_version,
        why_this_prompt=prompt.why_this_prompt,
        quality_scores=prompt.quality_scores,
    )


def _project_response(project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        status=project.status.value,
        topic=project.input.topic,
        duration_seconds=project.input.duration_seconds,
        current_scene_number=project.current_scene_number,
        total_scenes=len(project.scenes),
        story_hook=project.story_hook,
        story_central_claim=project.story_central_claim,
        story_ending=project.story_ending,
        facts=[
            FactResponse(
                id=fact.id,
                text=fact.text,
                status=fact.status.value,
                confidence=fact.confidence,
                sources=fact.sources,
                notes=fact.notes,
                approved_for_narration=fact.approved_for_narration,
            )
            for fact in project.facts
        ],
        scenes=[SceneResponse(**scene.__dict__) for scene in project.scenes],
        continuity=project.continuity.__dict__,
        prompts=[_prompt_response(prompt) for prompt in project.prompts.values()],
    )


@router.post("/api/projects", response_model=ProjectResponse, tags=["projects"])
def create_project(request: ProjectCreateRequest) -> ProjectResponse:
    project = project_service.create(
        ProjectInput(
            topic=request.topic,
            facts=request.facts,
            source_urls=request.source_urls,
            language=request.language,
            tone=request.tone,
            audience=request.audience,
            visual_preferences=request.visual_preferences,
            duration_seconds=request.duration_seconds,
        )
    )
    return _project_response(project)


@router.get("/api/projects/{project_id}", response_model=ProjectResponse, tags=["projects"])
def get_project(project_id: UUID) -> ProjectResponse:
    try:
        return _project_response(project_service.repository.get(project_id))
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


@router.post(
    "/api/projects/{project_id}/generate",
    response_model=PromptResponse,
    tags=["prompts"],
)
def generate_first_prompt(project_id: UUID) -> PromptResponse:
    try:
        return _prompt_response(project_service.generate_next(project_id))
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/api/projects/{project_id}/prompts/next",
    response_model=PromptResponse,
    tags=["prompts"],
)
def generate_next_prompt(project_id: UUID) -> PromptResponse:
    return generate_first_prompt(project_id)


@router.post(
    "/api/projects/{project_id}/prompts/{scene_number}/regenerate",
    response_model=PromptResponse,
    tags=["prompts"],
)
def regenerate_prompt(project_id: UUID, scene_number: int) -> PromptResponse:
    try:
        return _prompt_response(project_service.regenerate(project_id, scene_number))
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ProjectStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/api/projects/{project_id}/export",
    response_model=ExportResponse,
    tags=["export"],
)
def export_project(project_id: UUID) -> ExportResponse:
    try:
        project = project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    publishing = export_service.publishing_package(project)
    return ExportResponse(
        project_id=project.id,
        markdown=export_service.render_markdown(project),
        publishing=PublishingResponse(**publishing.__dict__),
        data=export_service.export_json(project),
    )
