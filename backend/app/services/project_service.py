from uuid import UUID

from app.domain.project import Project, ProjectInput, ProjectStatus, VideoPrompt
from app.services.prompt_pipeline import PromptGenerationPipeline, StoryArchitect


class ProjectNotFoundError(LookupError):
    pass


class ProjectStateError(ValueError):
    pass


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self._projects: dict[UUID, Project] = {}

    def save(self, project: Project) -> Project:
        self._projects[project.id] = project
        return project

    def get(self, project_id: UUID) -> Project:
        try:
            return self._projects[project_id]
        except KeyError as exc:
            raise ProjectNotFoundError(str(project_id)) from exc


class ProjectService:
    def __init__(self, repository: InMemoryProjectRepository | None = None) -> None:
        self.repository = repository or InMemoryProjectRepository()
        self.story_architect = StoryArchitect()
        self.prompt_pipeline = PromptGenerationPipeline()

    def create(self, project_input: ProjectInput) -> Project:
        project = Project(input=project_input, status=ProjectStatus.INPUT_RECEIVED)
        self.story_architect.create(project)
        project.status = ProjectStatus.SCENES_PLANNED
        self.repository.save(project)
        return project

    def generate_next(self, project_id: UUID) -> VideoPrompt:
        project = self.repository.get(project_id)
        next_number = project.current_scene_number + 1
        if next_number > len(project.scenes):
            raise ProjectStateError("All prompts have already been generated.")

        existing = project.prompts.get(next_number)
        if existing is not None:
            return existing

        prompt = self.prompt_pipeline.generate(project, project.scenes[next_number - 1])
        project.prompts[next_number] = prompt
        project.current_scene_number = next_number
        project.status = (
            ProjectStatus.COMPLETED
            if next_number == len(project.scenes)
            else ProjectStatus.AWAITING_NEXT
        )
        self.repository.save(project)
        return prompt
