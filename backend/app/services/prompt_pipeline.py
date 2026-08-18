from app.domain.generation import GenerationContext, VisualDirection
from app.domain.project import Project, Scene, VideoPrompt
from app.providers.base import LLMProvider
from app.providers.mock import GLOBAL_POLICY, MockProvider
from app.providers.schemas import NARRATION_SCHEMA, STORY_SCHEMA, VISUAL_SCHEMA
from app.services.narration_validator import draft_narration
from app.services.prompt_validator import validate_prompt


class StoryArchitect:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def create(self, project: Project) -> None:
        if self.provider is None or self.provider.name == "mock":
            MockProvider().create_story(project)
            return

        result = self.provider.generate_json(
            system_prompt=(
                "You are a story architect for animated YouTube Shorts. "
                "Use only the supplied topic and facts. Plan exactly the requested number of scenes."
            ),
            user_prompt=(
                f"Topic: {project.input.topic}\nFacts: {project.input.facts}\n"
                f"Language: {project.input.language}\nTone: {project.input.tone}\n"
                f"Scene count: {project.input.duration_seconds // 10}"
            ),
            response_schema=STORY_SCHEMA,
        )
        project.story_hook = result["hook"]
        project.story_central_claim = result["central_claim"]
        project.story_ending = result["ending"]
        project.scenes = [
            Scene(number=index, purpose=item["purpose"], summary=item["summary"], previous_scene_number=index - 1 if index > 1 else None)
            for index, item in enumerate(result["scenes"], start=1)
        ][: project.input.duration_seconds // 10]
        project.continuity = project.continuity


class NarrationWriter:
    _scripts = {
        "origin": "Every big story starts with one surprisingly small idea.",
        "breakthrough": "Then one turning point helped that idea travel far beyond its beginning.",
        "global_impact": "Today, that original spark connects with people around the world.",
    }

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def write(self, scene: Scene, project: Project):
        if self.provider is None or self.provider.name == "mock":
            text = self._scripts.get(scene.purpose, scene.summary)
        else:
            result = self.provider.generate_json(
                system_prompt=(
                    "Write concise, accurate narration for one animated YouTube Short scene. "
                    "Use no more than 20 words and end with a complete sentence."
                ),
                user_prompt=(
                    f"Language: {project.input.language}\nTone: {project.input.tone}\n"
                    f"Scene purpose: {scene.purpose}\nScene summary: {scene.summary}\n"
                    f"Approved topic facts: {project.input.facts}"
                ),
                response_schema=NARRATION_SCHEMA,
            )
            text = result["text"]
        return draft_narration(text)


class VisualDirector:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def direct(self, context: GenerationContext) -> VisualDirection:
        scene = context.scene
        transition = (
            f"Continue from Scene {scene.previous_scene_number}"
            if scene.previous_scene_number
            else "Open with a strong visual hook"
        )
        if self.provider is not None and self.provider.name != "mock":
            result = self.provider.generate_json(
                system_prompt=(
                    "You are a visual director. Create only original, clearly animated, "
                    "non-photorealistic visuals. Preserve the supplied continuity lock."
                ),
                user_prompt=(
                    f"Animation style: {context.project.continuity.animation_style}\n"
                    f"Palette: {context.project.continuity.palette}\n"
                    f"Camera language: {context.project.continuity.camera_language}\n"
                    f"Scene: {scene.summary}\nPrevious scene: {scene.previous_scene_number}"
                ),
                response_schema=VISUAL_SCHEMA,
            )
            return VisualDirection(**result)
        return VisualDirection(
            story_action=scene.summary,
            camera=context.project.continuity.camera_language,
            composition="Keep the main subject centered within the vertical mobile-safe frame.",
            transition=transition,
        )


class PromptComposer:
    def compose(self, context: GenerationContext, narration, visual: VisualDirection) -> VideoPrompt:
        project, scene = context.project, context.scene
        text = f"""{GLOBAL_POLICY}

PROJECT CONTINUITY
- Animation: {project.continuity.animation_style}
- Palette: {project.continuity.palette}
- Camera: {project.continuity.camera_language}
- Narration voice: {project.continuity.voice_description}
- Same original animated character designs and voice across every scene.

SCENE {scene.number}/{len(project.scenes)} — {scene.purpose}
STORY ACTION
{visual.story_action}

CAMERA AND COMPOSITION
- Camera: {visual.camera}
- Composition: {visual.composition}
- Transition: {visual.transition}

NARRATION
Use the locked narration voice. Finish speaking before 9 seconds:
\"{narration.text}\"

CAPTIONS
Burn synchronized, mobile-safe captions into the video with short readable lines.

AUDIO
Use restrained cinematic music and subtle animated sound effects. Keep narration clear.
Reserve the final second for a clean hold or transition; never cut speech abruptly.

SAFETY
Use only original animated people and environments. No real-looking humans, real-person
likenesses, prominent characters, logos, trademarks, or live-action imagery."""
        return VideoPrompt(
            project_id=project.id,
            scene_number=scene.number,
            total_scenes=len(project.scenes),
            text=text,
            narration=narration.text,
            narration_word_count=narration.word_count,
            estimated_narration_seconds=narration.estimated_seconds,
        )


class PromptGenerationPipeline:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.narration_writer = NarrationWriter(provider)
        self.visual_director = VisualDirector(provider)
        self.composer = PromptComposer()

    def generate(self, project: Project, scene: Scene) -> VideoPrompt:
        context = GenerationContext(project=project, scene=scene)
        narration = self.narration_writer.write(scene, project)
        visual = self.visual_director.direct(context)
        prompt = self.composer.compose(context, narration, visual)
        validate_prompt(prompt, context.contract)
        return prompt
