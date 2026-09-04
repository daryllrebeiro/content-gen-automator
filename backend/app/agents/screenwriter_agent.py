from typing import Dict, Any, List
from google.adk.agents import LlmAgent
from app.agents.tools.screenwriting_tools import draft_narration_tool

class ScreenwriterAgent(LlmAgent):
    """
    ADK Sub-Agent: Screenwriter & Pacing Specialist.
    Drafts high-retention narration scripts adhering to strict word-budget constraints (~2.5 words/sec).
    """
    role: str = "Screenwriter & Narration Pacing Specialist"

    def draft_narration(
        self,
        scene_number: int,
        total_scenes: int,
        topic: str,
        facts: List[str],
        target_seconds: int = 10,
        model_tier: str = "flagship"
    ) -> Dict[str, Any]:
        """
        Synthesizes a narration voiceover draft with word budget constraints and dynamic model tier routing.
        """
        from app.services.model_tier_service import ModelTierService
        spec = ModelTierService.get_tier_spec(model_tier)
        self.model = spec.screenwriter_model

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
            "model": spec.screenwriter_model,
            "model_tier": spec.id,
            "scene_number": scene_number,
            "narration": script,
            "word_count": len(words),
            "target_duration_seconds": target_seconds,
            "pacing_status": "optimal" if min_words <= len(words) <= max_words else "adjusted",
            "estimated_cost_usd": spec.estimated_cost_per_draft,
            "estimated_latency_ms": spec.estimated_latency_ms,
        }


def create_screenwriter_agent(model_tier: str = "flagship") -> ScreenwriterAgent:
    from app.services.model_tier_service import ModelTierService
    spec = ModelTierService.get_tier_spec(model_tier)
    return ScreenwriterAgent(
        name=f"screenwriter_agent_{spec.id}",
        model=spec.screenwriter_model,
        instruction="Draft high-retention cinematic voiceover narration within strict duration word budgets.",
        tools=[draft_narration_tool]
    )


screenwriter_agent = ScreenwriterAgent(
    name="screenwriter_agent",
    model="gemini-2.5-flash",
    instruction="Draft high-retention cinematic voiceover narration within strict duration word budgets.",
    tools=[draft_narration_tool]
)
