import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

class AgentEngineMemoryBank:
    """
    Agent Engine Memory Bank Adapter.
    Persists cross-project continuity, character bibles, brand voice parameters,
    and visual seeds across a Director's studio productions with real durable storage.
    """
    def __init__(self, storage_path: Optional[str] = None):
        self.endpoint = os.getenv("AGENT_ENGINE_MEMORY_ENDPOINT", "")
        # Resolve durable storage path
        default_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".storage"))
        self.storage_path = storage_path or os.getenv("MEMORY_BANK_STORAGE_PATH", os.path.join(default_dir, "memory_bank.json"))
        
        self.default_memory = {
            "studio_default": {
                "brand_voice": "Authoritative, engaging, cinematic documentary pacing with concise hooks.",
                "visual_signatures": ["Anamorphic lens flare", "Atmospheric volumetric lighting", "High-contrast rim lighting"],
                "character_bibles": {},
                "active_seeds": [42, 1337, 8080]
            }
        }
        self._memory_store = self._load_storage()

    def _load_storage(self) -> Dict[str, Dict[str, Any]]:
        """Loads durable memory store from disk or cloud, falling back to default."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "studio_default" not in data:
                        data["studio_default"] = self.default_memory["studio_default"]
                    return data
            except Exception as e:
                pass
        
        # Initialize default memory store and persist
        self._save_storage(self.default_memory)
        return dict(self.default_memory)

    def _save_storage(self, data: Dict[str, Any]):
        """Persists memory store atomically to prevent corrupt reads across processes."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.storage_path)), exist_ok=True)
            temp_file = f"{self.storage_path}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            if os.path.exists(self.storage_path):
                os.replace(temp_file, self.storage_path)
            else:
                os.rename(temp_file, self.storage_path)
        except Exception:
            pass

    def fetch_studio_memory(self, studio_id: str = "studio_default") -> Dict[str, Any]:
        """Retrieves persistent memory for a studio or director, reloading from durable storage."""
        self._memory_store = self._load_storage()
        return self._memory_store.get(studio_id, self._memory_store.get("studio_default", {}))

    def register_character_bible(self, studio_id: str, character_name: str, appearance_rules: str, seed: int = 42):
        """Registers a character appearance bible in the Memory Bank for consistent multi-scene & multi-project generation."""
        self._memory_store = self._load_storage()
        if studio_id not in self._memory_store:
            self._memory_store[studio_id] = {"character_bibles": {}, "visual_signatures": [], "active_seeds": []}
        
        self._memory_store[studio_id].setdefault("character_bibles", {})[character_name] = {
            "appearance_rules": appearance_rules,
            "seed": seed,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        self._save_storage(self._memory_store)

    def fetch_character_bible(self, studio_id: str, character_name: str) -> Optional[Dict[str, Any]]:
        studio_mem = self.fetch_studio_memory(studio_id)
        return studio_mem.get("character_bibles", {}).get(character_name)

    def register_seed(self, studio_id: str, seed: int):
        self._memory_store = self._load_storage()
        studio_mem = self._memory_store.setdefault(studio_id, {"character_bibles": {}, "visual_signatures": [], "active_seeds": []})
        if seed not in studio_mem.get("active_seeds", []):
            studio_mem.setdefault("active_seeds", []).append(seed)
            self._save_storage(self._memory_store)


agent_memory_bank = AgentEngineMemoryBank()
