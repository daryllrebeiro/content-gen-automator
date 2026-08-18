from app.domain.project import Project, VideoPrompt


class QualityScorer:
    def score(self, project: Project, prompt: VideoPrompt) -> dict[str, float]:
        timing = 1.0 if prompt.estimated_narration_seconds < 9 else 0.0
        structure_sections = [
            "FORMAT",
            "CONTINUITY LOCK",
            "SCENE / VISUAL STORY",
            "NARRATION — EXACT SCRIPT",
            "CAPTIONS",
            "AUDIO",
            "SAFETY",
            "FINAL GENERATION REQUIREMENTS",
        ]
        structure = sum(section in prompt.text for section in structure_sections) / len(structure_sections)
        continuity = 1.0 if len(prompt.continuity_lock) >= 8 and project.continuity.voice_id else 0.0
        safety = 1.0 if "photorealistic" in prompt.text and "live-action" in prompt.text else 0.0
        fact_score = 1.0 if all(fact.approved_for_narration for fact in project.facts) else 0.8
        hook_score = 1.0 if len(project.story_hook.split()) >= 6 else 0.7
        clarity = 1.0 if prompt.beats and prompt.narration else 0.0
        overall = round(sum([hook_score, clarity, timing, continuity, fact_score, safety, structure]) / 7, 2)
        return {
            "hook": round(hook_score, 2),
            "clarity": round(clarity, 2),
            "timing": round(timing, 2),
            "continuity": round(continuity, 2),
            "fact_grounding": round(fact_score, 2),
            "safety": round(safety, 2),
            "structure": round(structure, 2),
            "overall": overall,
        }

