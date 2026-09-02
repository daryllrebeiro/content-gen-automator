import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

class AgentEngineMemoryBank:
    """
    Agent Engine Memory Bank Adapter.
    Persists cross-project continuity, character bibles, brand voice parameters,
    and visual seeds across a Director's studio productions.
    """
    def __init__(self):
        self.endpoint = os.getenv("AGENT_ENGINE_MEMORY_ENDPOINT", "")
        self._memory_store: Dict[str, Dict[str, Any]] = {
            "studio_default": {
                "brand_voice": "Authoritative, engaging, cinematic documentary pacing with concise hooks.",
                "visual_signatures": ["Anamorphic lens flare", "Atmospheric volumetric lighting", "High-contrast rim lighting"],
                "character_bibles": {},
                "active_seeds": [42, 1337, 8080]
            }
        }

    def fetch_studio_memory(self, studio_id: str = "studio_default") -> Dict[str, Any]:
        """
        Retrieves persistent memory for a studio or director.
        """
        return self._memory_store.get(studio_id, self._memory_store["studio_default"])

    def register_character_bible(self, studio_id: str, character_name: str, appearance_rules: str, seed: int = 42):
        """
        Registers a character appearance bible in the Memory Bank for consistent multi-scene & multi-project generation.
        """
        if studio_id not in self._memory_store:
            self._memory_store[studio_id] = {"character_bibles": {}, "visual_signatures": [], "active_seeds": []}
        
        self._memory_store[studio_id]["character_bibles"][character_name] = {
            "appearance_rules": appearance_rules,
            "seed": seed,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    def fetch_character_bible(self, studio_id: str, character_name: str) -> Optional[Dict[str, Any]]:
        studio_mem = self.fetch_studio_memory(studio_id)
        return studio_mem.get("character_bibles", {}).get(character_name)

    def register_seed(self, studio_id: str, seed: int):
        studio_mem = self.fetch_studio_memory(studio_id)
        if seed not in studio_mem.get("active_seeds", []):
            studio_mem.setdefault("active_seeds", []).append(seed)


agent_memory_bank = AgentEngineMemoryBank()
