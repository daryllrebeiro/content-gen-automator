from typing import Dict, Any, List, Optional
from google.adk.agents import LlmAgent
from app.adapters.agent_engine_memory import agent_memory_bank
from app.agents.tools.continuity_tools import (
    register_seed_tool,
    fetch_character_bible_tool,
    fetch_continuity_lock_tool
)

class ContinuityAgent(LlmAgent):
    """
    ADK Sub-Agent: Character & Visual Continuity Specialist.
    Maintains seed consistency, visual anchors, and character appearance bibles across scenes and projects.
    """
    role: str = "Continuity & Character Bible Specialist"

    def get_continuity_lock(self, studio_id: str, scene_number: int) -> Dict[str, Any]:
        """
        Retrieves active seeds and style continuity locks from Agent Engine Memory Bank.
        """
        memory = agent_memory_bank.fetch_studio_memory(studio_id)
        seeds = memory.get("active_seeds", [42])
        seed = seeds[(scene_number - 1) % len(seeds)]
        
        return {
            "agent": "ContinuityAgent",
            "scene_number": scene_number,
            "seed": seed,
            "brand_voice": memory.get("brand_voice", ""),
            "visual_signatures": memory.get("visual_signatures", []),
        }


continuity_agent = ContinuityAgent(
    name="continuity_agent",
    model="gemini-2.5-flash",
    instruction="Maintain cross-scene visual seeds and character appearance bibles using Memory Bank tools.",
    tools=[register_seed_tool, fetch_character_bible_tool, fetch_continuity_lock_tool]
)
