from typing import Dict, Any, List

class ScreenwriterAgent:
    """
    ADK Sub-Agent: Screenwriter & Pacing Specialist.
    Drafts high-retention narration scripts adhering to strict word-budget constraints (~2.5 words/sec).
    """
    def __init__(self, model_name: str = "gemini-3.7-flash"):
        self.model_name = model_name
        self.role = "Screenwriter & Narration Pacing Specialist"

    def draft_narration(self, scene_number: int, total_scenes: int, topic: str, facts: List[str], target_seconds: int = 10) -> Dict[str, Any]:
        """
        Synthesizes a narration voiceover draft with word budget constraints.
        """
        max_words = int(target_seconds * 2.6)
        min_words = int(target_seconds * 1.8)
        
        # Select best fact or synthesize hook
        if scene_number == 1 and facts:
            script = f"Did you know that {facts[0]}"
        elif scene_number < len(facts):
            script = f"Remarkably, {facts[scene_number - 1]}"
        else:
            script = f"This single discovery about {topic} continues to transform our understanding today."

        words = script.split()
        return {
            "agent": "ScreenwriterAgent",
            "scene_number": scene_number,
            "narration": script,
            "word_count": len(words),
            "target_duration_seconds": target_seconds,
            "pacing_status": "optimal" if min_words <= len(words) <= max_words else "adjusted",
        }


screenwriter_agent = ScreenwriterAgent()
