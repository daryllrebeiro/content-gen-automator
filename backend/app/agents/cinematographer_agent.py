from typing import Dict, Any, List, Optional
from google.adk.agents import LlmAgent
from app.agents.tools.cinematography_tools import synthesize_visual_prompt_tool

class CinematographerAgent(LlmAgent):
    """
    ADK Sub-Agent: Cinematographer & Visual Directive Specialist.
    Translates script moments into rich camera, lighting, and movement directives for diffusion video models.
    Supports multimodal mood-board frame input.
    """
    role: str = "Cinematographer & Visual Prompt Synthesizer"

    def synthesize_visual_prompt(
        self,
        scene_number: int,
        topic: str,
        narration: str,
        visual_style: str = "stylized cinematic 3D animation",
        moodboard_image_url: Optional[str] = None,
        continuity_seed: Optional[int] = 42
    ) -> Dict[str, Any]:
        """
        Synthesizes visual camera and lighting prompt for generative video diffusion models.
        """
        camera_moves = ["Slow macro zoom-in", "Dynamic volumetric panning shot", "Intimate shallow depth-of-field tracking shot"]
        chosen_camera = camera_moves[(scene_number - 1) % len(camera_moves)]

        prompt_text = (
            f"Cinematic 4K vertical shot of {topic}. {chosen_camera} capturing hyper-detailed textures. "
            f"Dramatic atmospheric volumetric lighting with vivid rim light, {visual_style}. "
            f"Color palette: deep obsidian tones accented with glowing bioluminescent highlights. Rendered in 60fps."
        )

        return {
            "agent": "CinematographerAgent",
            "scene_number": scene_number,
            "visual_prompt": prompt_text,
            "camera_directive": chosen_camera,
            "lighting_setup": "Volumetric shafts with dual-tone rim light",
            "visual_style": visual_style,
            "seed": continuity_seed,
            "moodboard_processed": bool(moodboard_image_url),
        }


cinematographer_agent = CinematographerAgent(
    name="cinematographer_agent",
    model="gemini-2.5-flash",
    instruction="Synthesize visual camera, lighting, and movement directives for video diffusion pipelines.",
    tools=[synthesize_visual_prompt_tool]
)
