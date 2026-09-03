#!/usr/bin/env python
"""
Verification Script: Cross-Process Persistence for Agent Engine Memory Bank & Vertex Search.
Executes distinct Python processes to prove durable round-trip storage.
"""

import os
import sys
import subprocess

def run_step_1_write(storage_dir: str):
    """Process 1: Writes character bible, seed lock, and style guideline."""
    py_code = f"""
import sys, os
sys.path.insert(0, os.path.abspath('backend'))
os.environ['MEMORY_BANK_STORAGE_PATH'] = os.path.join(r'{storage_dir}', 'test_memory.json')
os.environ['VERTEX_SEARCH_STORAGE_PATH'] = os.path.join(r'{storage_dir}', 'test_search.json')

from app.adapters.agent_engine_memory import AgentEngineMemoryBank
from app.adapters.vertex_search import VertexSearchGroundingAdapter

mem = AgentEngineMemoryBank(os.environ['MEMORY_BANK_STORAGE_PATH'])
mem.register_character_bible(
    studio_id="studio_cyberpunk",
    character_name="Aria Voss",
    appearance_rules="Cybernetic optic visor glowing cyan, matte obsidian combat vest.",
    seed=9090
)
mem.register_seed("studio_cyberpunk", 9090)

search = VertexSearchGroundingAdapter(os.environ['VERTEX_SEARCH_STORAGE_PATH'])
search.register_guideline("color_grading", "Teal-and-orange grading with neon bioluminescent highlights.")

print("PROCESS_1_WRITE_SUCCESS")
"""
    res = subprocess.run([sys.executable, "-c", py_code], capture_output=True, text=True, check=True)
    assert "PROCESS_1_WRITE_SUCCESS" in res.stdout, f"Process 1 failed: {res.stderr}"
    print("[PASS] Process 1: Character bible, seed lock, and guideline written and committed to disk.")


def run_step_2_read(storage_dir: str):
    """Process 2: Fresh separate process reads and verifies the written data."""
    py_code = f"""
import sys, os
sys.path.insert(0, os.path.abspath('backend'))
os.environ['MEMORY_BANK_STORAGE_PATH'] = os.path.join(r'{storage_dir}', 'test_memory.json')
os.environ['VERTEX_SEARCH_STORAGE_PATH'] = os.path.join(r'{storage_dir}', 'test_search.json')

from app.adapters.agent_engine_memory import AgentEngineMemoryBank
from app.adapters.vertex_search import VertexSearchGroundingAdapter

# Instantiate in fresh process context
mem = AgentEngineMemoryBank(os.environ['MEMORY_BANK_STORAGE_PATH'])
bible = mem.fetch_character_bible("studio_cyberpunk", "Aria Voss")
assert bible is not None, "Character bible Aria Voss not found!"
assert bible["seed"] == 9090, f"Expected seed 9090, got {{bible['seed']}}"
assert "Cybernetic optic visor" in bible["appearance_rules"], "Appearance rules mismatch!"

studio_mem = mem.fetch_studio_memory("studio_cyberpunk")
assert 9090 in studio_mem.get("active_seeds", []), "Seed 9090 not found in studio active seeds!"

search = VertexSearchGroundingAdapter(os.environ['VERTEX_SEARCH_STORAGE_PATH'])
context = search.retrieve_grounding_context()
matched = context["matched_guidelines"]
assert any("Teal-and-orange" in g for g in matched), "Custom guideline not found in fresh process read!"

print("PROCESS_2_READ_SUCCESS")
"""
    res = subprocess.run([sys.executable, "-c", py_code], capture_output=True, text=True, check=True)
    assert "PROCESS_2_READ_SUCCESS" in res.stdout, f"Process 2 failed: {res.stderr}"
    print("[PASS] Process 2: Fresh independent Python process verified data fidelity.")


def main():
    test_storage_dir = os.path.abspath(".storage_test")
    os.makedirs(test_storage_dir, exist_ok=True)
    try:
        print("Running Cross-Process Memory Bank & Vertex Search Round-Trip Probe...")
        run_step_1_write(test_storage_dir)
        run_step_2_read(test_storage_dir)
        print("=====================================================================")
        print("ALL PROCESS BOUNDARIES VERIFIED: Durable Persistence Confirmed!")
        print("=====================================================================")
    finally:
        for fname in ["test_memory.json", "test_search.json", "test_memory.json.tmp", "test_search.json.tmp"]:
            p = os.path.join(test_storage_dir, fname)
            if os.path.exists(p):
                os.remove(p)
        if os.path.exists(test_storage_dir):
            try:
                os.rmdir(test_storage_dir)
            except Exception:
                pass

if __name__ == "__main__":
    main()
