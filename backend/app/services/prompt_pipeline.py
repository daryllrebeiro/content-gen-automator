from app.domain.generation import GenerationContext, VisualDirection
from app.domain.project import Project, Scene, VideoPrompt
from app.providers.base import LLMProvider
from app.providers.mock import GLOBAL_POLICY, MockProvider
from app.providers.schemas import NARRATION_SCHEMA, STORY_SCHEMA, VISUAL_SCHEMA
from app.services.narration_validator import draft_narration
from app.services.prompt_validator import validate_prompt
from app.services.quality_scorer import QualityScorer


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
                    f"Approved topic facts: {project.facts and [fact.text for fact in project.facts if fact.approved_for_narration]}"
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
        beats = {
            "origin": [
                {"time_range": "0–3 seconds", "title": "The small beginning", "details": ["Open on a tiny animated discovery in an ordinary setting.", "Use a slow cinematic reveal to establish the story world."]},
                {"time_range": "3–6 seconds", "title": "The idea takes shape", "details": ["Show animated people experimenting with the discovery.", "Keep all characters generic, stylized, and clearly non-realistic."]},
                {"time_range": "6–9 seconds", "title": "The first sign of growth", "details": ["Show the idea spreading from one small place to a larger group.", "Build visual momentum without changing the animation style."]},
                {"time_range": "9–10 seconds", "title": "Transition hook", "details": ["End on a clear visual element that can continue into the next clip.", "Hold the final image for the last second without spoken dialogue."]},
            ],
            "breakthrough": [
                {"time_range": "0–3 seconds", "title": "Continue the story", "details": ["Begin directly from the previous clip’s final visual beat.", "Show the original idea becoming more organized."]},
                {"time_range": "3–6 seconds", "title": "The turning point", "details": ["Visualize the breakthrough that allows the idea to travel farther.", "Use a clear cinematic transformation rather than a disconnected montage."]},
                {"time_range": "6–9 seconds", "title": "Expansion", "details": ["Move through increasingly connected animated locations.", "Make the scale visibly larger while preserving the same characters and palette."]},
                {"time_range": "9–10 seconds", "title": "Transition hook", "details": ["Create a visual bridge into the worldwide impact scene.", "Leave the final second for music and sound effects only."]},
            ],
            "global_impact": [
                {"time_range": "0–3 seconds", "title": "From the past to today", "details": ["Begin exactly from the previous clip’s transition image.", "Reveal how the original idea appears in the modern world."]},
                {"time_range": "3–6 seconds", "title": "Beyond the original setting", "details": ["Show a cinematic montage of the idea’s modern uses.", "Keep the visual explanation immediately understandable."]},
                {"time_range": "6–9 seconds", "title": "Worldwide reach", "details": ["Pull outward to show animated cities, regions, and connected communities.", "Build toward a clean global visual summary."]},
                {"time_range": "9–10 seconds", "title": "Final reveal", "details": ["End with the original small beginning visually connected to the worldwide result.", "Hold the final image for a clean end card or CTA."]},
            ],
        }.get(scene.purpose, [])
        return VisualDirection(
            story_action=scene.summary,
            camera=context.project.continuity.camera_language,
            composition="Keep the main subject centered within the vertical mobile-safe frame.",
            transition=transition,
            beats=beats,
        )


class PromptComposer:
    def compose(self, context: GenerationContext, narration, visual: VisualDirection) -> VideoPrompt:
        project, scene = context.project, context.scene
        continuity_lock = [
            "Same fully animated cinematic style in every clip.",
            "Same stylized, clearly non-realistic animated human design.",
            "Humans must never appear photorealistic or resemble identifiable real people.",
            "No named historical figures, prominent fictional characters, logos, or trademarks.",
            f"Same cinematic lighting, palette, camera language, and visual quality: {project.continuity.palette}.",
            f"Same exact narration voice: {project.continuity.voice_description}.",
            "Video duration: exactly 10 seconds.",
            "Aspect ratio: 9:16 vertical.",
            "Narration must finish by approximately 9 seconds, leaving the final second without spoken dialogue.",
        ]
        captions = self._caption_lines(narration.text)
        audio_plan = [
            "Use the exact same narrator voice as every other clip.",
            "Maintain the same warm, authoritative, cinematic documentary delivery.",
            "Layer subtle animated sound effects that match the scene action.",
            "Music should support the story and build toward the scene transition without overpowering narration.",
            "CRITICAL AUDIO TIMING: spoken narration must finish by approximately 9.0 seconds.",
            "Reserve the final approximately 1 second for music, ambient sound, and visual transition only.",
        ]
        final_requirements = [
            "Make the clip feel like one continuous cinematic animated story, not unrelated shots.",
            "Keep every character, environment, voice, and animation choice consistent with the continuity lock.",
            "Do not use live-action footage or photorealistic humans.",
            "Do not depict or imitate any specific famous person or recognizable copyrighted character.",
            "End on a visual beat that naturally sets up the next clip or final CTA.",
        ]
        approved_fact_count = sum(1 for fact in project.facts if fact.approved_for_narration)
        why_this_prompt = [
            f"Scene {scene.number} fulfills the {scene.purpose} story purpose.",
            "Continuity inherited from the project-level animation, palette, camera, and voice locks.",
            f"Narration validated at {narration.word_count} words / approximately {narration.estimated_seconds} seconds.",
            "The 10-second video contract leaves the final second free from spoken dialogue.",
            f"{approved_fact_count} approved factual claims were available to narration." if approved_fact_count else "No factual claim was promoted into narration without verification.",
            "Prompt passed structured-section and animated-only safety validation.",
        ]
        beat_text = "\n\n".join(
            f"**{beat['time_range']} — {beat['title']}**\n" + "\n".join(f"- {detail}" for detail in beat["details"])
            for beat in visual.beats
        )
        text = f"""{GLOBAL_POLICY}

FORMAT
10-second YouTube Shorts clip, 9:16 vertical, cinematic fully animated video.

CONTINUITY LOCK — MUST REMAIN IDENTICAL TO ALL OTHER CLIPS
{chr(10).join(f"- {item}" for item in continuity_lock)}

SCENE / VISUAL STORY
Scene {scene.number}/{len(project.scenes)} — {scene.purpose}
Overall action: {visual.story_action}

{beat_text}

CAMERA AND COMPOSITION
- Camera language: {visual.camera}
- Composition: {visual.composition}
- Transition direction: {visual.transition}

NARRATION — EXACT SCRIPT
Use the locked narrator voice. The script must be spoken exactly as written:
\"{narration.text}\"

CAPTIONS
Synchronize captions precisely with the narration:
{chr(10).join(f'- "{line}"' for line in captions)}
Keep captions large, cinematic, mobile-readable, and safely inside the 9:16 frame.

AUDIO
{chr(10).join(f'- {item}' for item in audio_plan)}

SAFETY AND EXCLUSIONS
- Fully animated visuals only; no live-action footage or photorealistic humans.
- No identifiable real-person likenesses, named prominent figures, or recognizable copyrighted characters.
- No logos, trademarks, or imitation of a specific person.

FINAL GENERATION REQUIREMENTS
{chr(10).join(f'- {item}' for item in final_requirements)}
"""
        return VideoPrompt(
            project_id=project.id,
            scene_number=scene.number,
            total_scenes=len(project.scenes),
            text=text,
            narration=narration.text,
            narration_word_count=narration.word_count,
            estimated_narration_seconds=narration.estimated_seconds,
            beats=visual.beats,
            captions=captions,
            continuity_lock=continuity_lock,
            audio_plan=audio_plan,
            final_requirements=final_requirements,
            why_this_prompt=why_this_prompt,
        )

    @staticmethod
    def _caption_lines(text: str) -> list[str]:
        words = text.replace("—", " ").split()
        if len(words) <= 5:
            return [text]
        chunk_size = max(3, min(5, round(len(words) / 4)))
        return [" ".join(words[index:index + chunk_size]) for index in range(0, len(words), chunk_size)]


class PromptGenerationPipeline:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.narration_writer = NarrationWriter(provider)
        self.visual_director = VisualDirector(provider)
        self.composer = PromptComposer()
        self.quality_scorer = QualityScorer()

    def generate(self, project: Project, scene: Scene) -> VideoPrompt:
        context = GenerationContext(project=project, scene=scene)
        narration = self.narration_writer.write(scene, project)
        visual = self.visual_director.direct(context)
        prompt = self.composer.compose(context, narration, visual)
        validate_prompt(prompt, context.contract)
        prompt.quality_scores = self.quality_scorer.score(project, prompt)
        return prompt
