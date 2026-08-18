from dataclasses import asdict, dataclass

from app.domain.project import Project


@dataclass
class PublishingPackage:
    title: str
    description: str
    hashtags: list[str]
    pinned_comment: str


class ExportService:
    def publishing_package(self, project: Project) -> PublishingPackage:
        topic = project.input.topic.strip().rstrip(".!?")
        title = f"{topic} — The Story in 30 Seconds!"
        description = (
            f"{project.story_hook}\n\n{project.story_ending}\n\n"
            "This fully animated Short explains the story through a cinematic, "
            "mobile-first visual journey."
        )
        hashtags = ["#Shorts", "#YouTubeShorts", "#AnimatedShort", "#Documentary", "#DidYouKnow"]
        pinned_comment = f"What surprised you most about {topic.lower()}?"
        return PublishingPackage(title, description, hashtags, pinned_comment)

    def render_markdown(self, project: Project) -> str:
        publishing = self.publishing_package(project)
        lines = [
            f"# {project.input.topic}",
            "",
            "## Publishing Package",
            "",
            f"### Title\n{publishing.title}",
            f"### Description\n{publishing.description}",
            f"### Hashtags\n{' '.join(publishing.hashtags)}",
            f"### Pinned Comment\n{publishing.pinned_comment}",
            "",
            "## Story",
            "",
            f"**Hook:** {project.story_hook}",
            f"**Central claim:** {project.story_central_claim}",
            f"**Ending:** {project.story_ending}",
            "",
            "## Continuity Lock",
            "",
            f"- Animation: {project.continuity.animation_style}",
            f"- Palette: {project.continuity.palette}",
            f"- Camera: {project.continuity.camera_language}",
            f"- Voice: {project.continuity.voice_description}",
            "",
            "## Facts",
            "",
        ]
        lines.extend(
            f"- `{fact.id}` [{fact.status.value}] {fact.text}"
            for fact in project.facts
        )
        lines.extend(["", "## Prompts", ""])
        for scene_number in sorted(project.prompts):
            prompt = project.prompts[scene_number]
            lines.extend(
                [
                    f"### Scene {prompt.scene_number}/{prompt.total_scenes} — Version {prompt.version_number}",
                    "",
                    "```text",
                    prompt.text,
                    "```",
                    "",
                ]
            )
        return "\n".join(lines)

    def export_json(self, project: Project) -> dict:
        publishing = self.publishing_package(project)
        return {
            "project_id": str(project.id),
            "topic": project.input.topic,
            "duration_seconds": project.input.duration_seconds,
            "status": project.status.value,
            "publishing": asdict(publishing),
            "story": {
                "hook": project.story_hook,
                "central_claim": project.story_central_claim,
                "ending": project.story_ending,
            },
            "continuity": asdict(project.continuity),
            "facts": [asdict(fact) | {"status": fact.status.value} for fact in project.facts],
            "prompts": [asdict(prompt) for prompt in project.prompts.values()],
            "prompt_history": {
                str(scene): [asdict(prompt) for prompt in prompts]
                for scene, prompts in project.prompt_history.items()
            },
        }

