from uuid import UUID
import os

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

        return GeminiProvider()

    def create(self, project_input: ProjectInput) -> Project:
        project = Project(input=project_input, status=ProjectStatus.INPUT_RECEIVED)
        self.fact_engine.ingest(project)
        self.story_architect.create(project)
        project.status = ProjectStatus.SCENES_PLANNED
        self.repository.save(project)
        return project

    def generate_next(self, project_id: UUID) -> VideoPrompt:
        project = self.repository.get(project_id)
        next_number = project.current_scene_number + 1
        if next_number > len(project.scenes):
            if project.scenes and project.scenes[-1].number in project.prompts:
                return project.prompts[project.scenes[-1].number]
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

    def regenerate(self, project_id: UUID, scene_number: int) -> VideoPrompt:
        project = self.repository.get(project_id)
        if scene_number < 1 or scene_number > len(project.scenes):
            raise ProjectStateError("Scene number is outside this project.")
        if scene_number not in project.prompts:
            raise ProjectStateError("Generate the scene once before regenerating it.")

        current = project.prompts[scene_number]
        history = project.prompt_history.setdefault(scene_number, [])
        history.append(current)
        regenerated = self.prompt_pipeline.generate(project, project.scenes[scene_number - 1])
        regenerated.version_number = current.version_number + 1
        regenerated.template_version = current.template_version
        project.prompts[scene_number] = regenerated
        self.repository.save(project)
        return regenerated
