from typing import Dict, Any, List, Optional
from app.adapters.agent_engine_memory import agent_memory_bank

class ContinuityAgent:
    """
    ADK Sub-Agent: Character & Visual Continuity Specialist.
    Maintains seed consistency, visual anchors, and character appearance bibles across scenes and projects.
    """
    def __init__(self, model_name: str = "gemini-3.7-flash"):
        self.model_name = model_name
        self.role = "Continuity & Character Bible Specialist"

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


continuity_agent = ContinuityAgent()
