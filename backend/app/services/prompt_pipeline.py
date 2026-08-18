from app.domain.generation import GenerationContext, VisualDirection
from app.domain.project import Project, Scene, VideoPrompt
from app.providers.mock import MockProvider
from app.services.narration_validator import draft_narration
from app.services.prompt_validator import validate_prompt


class StoryArchitect:
    def create(self, project: Project) -> None:
        MockProvider().create_story(project)


class NarrationWriter:
    _scripts = {
        "origin": "Every big story starts with one surprisingly small idea.",
        "breakthrough": "Then one turning point helped that idea travel far beyond its beginning.",
        "global_impact": "Today, that original spark connects with people around the world.",
    }

    def write(self, scene: Scene):
        return draft_narration(self._scripts.get(scene.purpose, scene.summary))


class VisualDirector:
    def direct(self, context: GenerationContext) -> VisualDirection:
        scene = context.scene
        transition = (
            f"Continue from Scene {scene.previous_scene_number}"
            if scene.previous_scene_number
            else "Open with a strong visual hook"
        )
        return VisualDirection(
            story_action=scene.summary,
            camera=context.project.continuity.camera_language,
            composition="Keep the main subject centered within the vertical mobile-safe frame.",
            transition=transition,
        )


class PromptComposer:
    def __init__(self, provider: MockProvider | None = None) -> None:
        self.provider = provider or MockProvider()

    def compose(self, context: GenerationContext, narration, visual: VisualDirection) -> VideoPrompt:
        # The provider owns the copy-ready policy language for now. This composer owns
        # the stage boundary so a real provider can replace it without changing the service.
        prompt = self.provider.generate_prompt(context.project, context.scene)
        prompt.narration = narration.text
        prompt.narration_word_count = narration.word_count
        prompt.estimated_narration_seconds = narration.estimated_seconds
        prompt.text += f"\n\nVISUAL DIRECTION\n- {visual.story_action}\n- Camera: {visual.camera}\n- Composition: {visual.composition}\n- Transition: {visual.transition}."
        return prompt


class PromptGenerationPipeline:
    def __init__(self) -> None:
        self.narration_writer = NarrationWriter()
        self.visual_director = VisualDirector()
        self.composer = PromptComposer()

    def generate(self, project: Project, scene: Scene) -> VideoPrompt:
        context = GenerationContext(project=project, scene=scene)
        narration = self.narration_writer.write(scene)
        visual = self.visual_director.direct(context)
        prompt = self.composer.compose(context, narration, visual)
        validate_prompt(prompt, context.contract)
        return prompt

