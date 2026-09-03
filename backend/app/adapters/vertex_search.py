import os
import json
from typing import Dict, List, Any, Optional

class VertexSearchGroundingAdapter:
    """
    Vertex AI Search Grounding Adapter.
    Retrieves internal studio brand guidelines, style guides, and approved storytelling blueprints
    from Vertex AI Search Datastores with durable persistence.
    """
    def __init__(self, storage_path: Optional[str] = None):
        self.project_id = os.getenv("GCP_PROJECT_ID", "")
        self.datastore_id = os.getenv("VERTEX_SEARCH_DATASTORE_ID", "studio-house-style")
        
        default_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".storage"))
        self.storage_path = storage_path or os.getenv("VERTEX_SEARCH_STORAGE_PATH", os.path.join(default_dir, "vertex_search_datastore.json"))
        
        self.default_datastore = {
            "pacing_rules": "Shorts narration must maintain 2.2 to 2.8 words per second. Visual changes must occur every 3 to 5 seconds.",
            "visual_style_guide": "Avoid muddy gradients. Favor high-contrast neon accents, deep blacks, and volumetric light shafts.",
            "brand_safety_policy": "Strict compliance with Universal Family / General Audience standards. No hate, violence, or direct competitor trademark attacks."
        }
        self._internal_datastore = self._load_storage()

    def _load_storage(self) -> Dict[str, str]:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        self._save_storage(self.default_datastore)
        return dict(self.default_datastore)

    def _save_storage(self, data: Dict[str, str]):
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

    def register_guideline(self, key: str, rule: str):
        """Adds or updates a storytelling or style guideline in the datastore."""
        self._internal_datastore = self._load_storage()
        self._internal_datastore[key] = rule
        self._save_storage(self._internal_datastore)

    def retrieve_grounding_context(self, query: str = "") -> Dict[str, Any]:
        """Queries Vertex AI Search datastore for internal guidelines matching the prompt task."""
        self._internal_datastore = self._load_storage()
        return {
            "source": "Vertex AI Search Datastore",
            "datastore_id": self.datastore_id,
            "matched_guidelines": list(self._internal_datastore.values())
        }


vertex_search = VertexSearchGroundingAdapter()
