import os
import tempfile
import json
from app.adapters.agent_engine_memory import AgentEngineMemoryBank
from app.adapters.vertex_search import VertexSearchGroundingAdapter

def test_memory_bank_durable_file_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "mem.json")
        mem1 = AgentEngineMemoryBank(storage_path)
        mem1.register_character_bible("studio_neo", "Kai Thorne", "Neon holographic trenchcoat", seed=777)
        mem1.register_seed("studio_neo", 777)

        # Instantiate brand new adapter pointing to same storage
        mem2 = AgentEngineMemoryBank(storage_path)
        bible = mem2.fetch_character_bible("studio_neo", "Kai Thorne")
        assert bible is not None
        assert bible["seed"] == 777
        assert "Neon holographic" in bible["appearance_rules"]

        studio = mem2.fetch_studio_memory("studio_neo")
        assert 777 in studio["active_seeds"]


def test_vertex_search_durable_file_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "search.json")
        search1 = VertexSearchGroundingAdapter(storage_path)
        search1.register_guideline("pacing", "Strict 2.5 words per second.")

        search2 = VertexSearchGroundingAdapter(storage_path)
        ctx = search2.retrieve_grounding_context()
        assert any("Strict 2.5 words per second." in g for g in ctx["matched_guidelines"])
