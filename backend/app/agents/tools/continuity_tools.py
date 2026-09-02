from typing import Dict, Any, Optional
from app.adapters.agent_engine_memory import agent_memory_bank

def register_seed_tool(studio_id: str, seed: int) -> Dict[str, Any]:
    """
    Registers an active visual seed in the Agent Engine Memory Bank for cross-scene continuity.
    
    Args:
        studio_id: Studio or Director ID.
        seed: Random integer seed to lock character and lighting consistency.
    """
    agent_memory_bank.register_seed(studio_id, seed)
    return {"status": "registered", "studio_id": studio_id, "seed": seed}

def fetch_character_bible_tool(studio_id: str, character_name: str) -> Dict[str, Any]:
    """
    Retrieves character visual appearance rules and persistent seed from Agent Engine Memory Bank.
    
    Args:
        studio_id: Studio or Director ID.
        character_name: Name of character to fetch appearance guidelines for.
    """
    bible = agent_memory_bank.fetch_character_bible(studio_id, character_name)
    return bible or {"found": False, "message": f"No character bible found for {character_name}"}

def fetch_continuity_lock_tool(studio_id: str, scene_number: int) -> Dict[str, Any]:
    """
    Locks and returns the persistent visual seed and brand voice parameters for a scene.
    
    Args:
        studio_id: Studio or Director ID.
        scene_number: 1-based index of current scene.
    """
    mem = agent_memory_bank.fetch_studio_memory(studio_id)
    seeds = mem.get("active_seeds", [42])
    seed = seeds[(scene_number - 1) % len(seeds)]
    return {
        "studio_id": studio_id,
        "scene_number": scene_number,
        "seed": seed,
        "brand_voice": mem.get("brand_voice", ""),
        "visual_signatures": mem.get("visual_signatures", [])
    }
