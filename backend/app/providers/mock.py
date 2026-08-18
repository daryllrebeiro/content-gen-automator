from app.domain.project import ContinuityProfile, Project, Scene, VideoPrompt


GLOBAL_POLICY = (
    "Fully animated cinematic YouTube Short, 9:16 vertical, exactly 10 seconds. "
    "No photorealistic humans, real-person likenesses, prominent fictional characters, "
    "logos, trademarks, or live-action footage. Narration must end by 9 seconds."
)


class MockProvider:
    """Deterministic provider used before connecting a real LLM."""

    name = "mock"

    def create_story(self, project: Project) -> None:
        topic = project.input.topic.strip()
        project.story_hook = f"What began as a small idea became a much bigger story: {topic}."
        project.story_central_claim = "A clear idea, repeated consistently, can grow beyond its original setting."
        project.story_ending = "The final scene connects the original spark to its wider impact."

        purposes = [("origin", "Show the small beginning and introduce the central idea.")]
        if project.input.duration_seconds >= 20:
            purposes.append(("breakthrough", "Show the turning point that makes the idea spread."))
        if project.input.duration_seconds >= 30:
            purposes.append(("global_impact", "Show the wider impact and land the takeaway."))

        project.scenes = [
            Scene(
                number=index,
                purpose=purpose,
                summary=summary,
                previous_scene_number=index - 1 if index > 1 else None,
            )
            for index, (purpose, summary) in enumerate(purposes, start=1)
        ]
        project.continuity = ContinuityProfile(
            animation_style=project.input.visual_preferences.get(
                "style", "stylized cinematic 3D animation"
            ),
            palette=project.input.visual_preferences.get(
                "palette", "warm amber, deep blue, and muted brown"
            ),
            camera_language=project.input.visual_preferences.get(
                "camera", "smooth animated documentary camera"
            ),
            continuity_rules=[
                "All scenes use the same clearly animated visual medium.",
                "Characters remain original, generic, and visually consistent.",
                "Use the same narration voice and audio identity in every scene.",
            ],
        )

    def generate_prompt(self, project: Project, scene: Scene) -> VideoPrompt:
        narration_by_purpose = {
            "origin": "Every big story starts with one surprisingly small idea.",
            "breakthrough": "Then one turning point helped that idea travel far beyond its beginning.",
            "global_impact": "Today, that original spark connects with people around the world.",
        }
        narration = narration_by_purpose.get(scene.purpose, scene.summary)
        previous = (
            f" Continue directly from Scene {scene.previous_scene_number}."
            if scene.previous_scene_number
            else " Open with a strong visual hook."
        )
        text = f"""{GLOBAL_POLICY}

PROJECT CONTINUITY
- Animation: {project.continuity.animation_style}
- Palette: {project.continuity.palette}
- Camera: {project.continuity.camera_language}
- Narration voice: {project.continuity.voice_description}
- {project.continuity.continuity_rules[0]}

SCENE {scene.number}/{len(project.scenes)} — {scene.purpose}
Create a cinematic animated sequence showing: {scene.summary}{previous}
Keep the visuals active for the full 10 seconds and end with a clean one-second hold.

NARRATION
Use the locked narration voice. Say only this script and finish speaking before 9 seconds:
\"{narration}\"

CAPTIONS
Burn the narration into synchronized, mobile-safe captions with short readable lines.

AUDIO
Use restrained cinematic music and subtle animated sound effects. Keep narration clear.
Do not cut speech abruptly; reserve the final second for ambient sound or transition.

SAFETY
Use only original animated people and environments. No real-looking humans, real-person
likenesses, prominent characters, logos, trademarks, or live-action imagery."""
        word_count = len(narration.split())
        estimated_seconds = round(word_count / 140 * 60, 1)
        return VideoPrompt(
            project_id=project.id,
            scene_number=scene.number,
            total_scenes=len(project.scenes),
            text=text,
            narration=narration,
            narration_word_count=word_count,
            estimated_narration_seconds=estimated_seconds,
        )
