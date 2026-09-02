from typing import Dict, Any, List
from uuid import UUID
from app.services.project_service import ProjectService
from app.adapters.agent_engine_memory import agent_memory_bank

project_service = ProjectService()

def fetch_project_state_tool(project_id: str) -> Dict[str, Any]:
    """
    Retrieves the complete state, storyboard, facts, and prompt history for a project.
    
    Args:
        project_id: UUID string of the project.
    """
    project = project_service.repository.get(UUID(project_id))
    return {
        "id": str(project.id),
        "status": project.status.value,
        "topic": project.topic,
        "scenes_total": len(project.scenes),
        "prompts_generated": len(project.prompts),
        "current_scene_target": project.current_scene_number,
    }

def fetch_character_bible_tool(studio_id: str, character_name: str) -> Dict[str, Any]:
    """
    Retrieves character visual appearance rules and seed from Agent Engine Memory Bank.
    
    Args:
        studio_id: Studio or Director ID.
        character_name: Name of character to fetch rules for.
    """
    bible = agent_memory_bank.fetch_character_bible(studio_id, character_name)
    return bible or {"found": False, "message": "No registered character bible found."}
