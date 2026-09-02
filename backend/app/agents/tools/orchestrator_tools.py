from typing import Dict, Any, List, Optional
from app.agents.research_agent import research_agent
from app.agents.screenwriter_agent import screenwriter_agent
from app.agents.cinematographer_agent import cinematographer_agent
from app.agents.continuity_agent import continuity_agent
from app.agents.governance_agent import governance_agent
from app.agents.publishing_agent import publishing_agent

def delegate_research_task(topic: str, tone: str = "curious documentary") -> Dict[str, Any]:
    """
    Delegates factual grounding and style retrieval to ResearchAgent (ADK A2A handoff).
    
    Args:
        topic: Story or documentary topic.
        tone: Narrative tone or mood.
    """
    return research_agent.ground_topic(topic, tone)

def delegate_screenplay_task(
    topic: str,
    scene_number: int,
    total_scenes: int,
    facts: Optional[List[str]] = None,
    target_seconds: int = 10
) -> Dict[str, Any]:
    """
    Delegates scriptwriting and word-budgeted narration pacing to ScreenwriterAgent (ADK A2A handoff).
    
    Args:
        topic: Scene subject matter.
        scene_number: Current scene index.
        total_scenes: Total scenes in project.
        facts: Grounded facts to incorporate.
        target_seconds: Desired narration duration.
    """
    return screenwriter_agent.draft_narration(scene_number, total_scenes, topic, facts or [], target_seconds)

def delegate_cinematography_task(
    scene_number: int,
    topic: str,
    narration: str,
    visual_style: str = "stylized cinematic 3D animation",
    continuity_seed: int = 42
) -> Dict[str, Any]:
    """
    Delegates visual prompt synthesis, camera directives, and lighting setups to CinematographerAgent (ADK A2A handoff).
    
    Args:
        scene_number: Current scene index.
        topic: Scene subject matter.
        narration: Voiceover text for the scene.
        visual_style: Visual rendering aesthetic.
        continuity_seed: Seed for stylistic consistency.
    """
    return cinematographer_agent.synthesize_visual_prompt(
        scene_number=scene_number,
        topic=topic,
        narration=narration,
        visual_style=visual_style,
        continuity_seed=continuity_seed
    )

def delegate_continuity_lock_task(studio_id: str, scene_number: int) -> Dict[str, Any]:
    """
    Delegates seed locking and brand voice continuity to ContinuityAgent (ADK A2A handoff).
    
    Args:
        studio_id: Studio or Director ID.
        scene_number: Current scene index.
    """
    return continuity_agent.get_continuity_lock(studio_id, scene_number)

def delegate_governance_audit_task(
    visual_prompt: str,
    narration: str,
    facts: Optional[List[str]] = None,
    project_id: str = ""
) -> Dict[str, Any]:
    """
    Delegates IBM watsonx safety and brand compliance audit to GovernanceAgent (ADK A2A handoff).
    
    Args:
        visual_prompt: Generated visual prompt text.
        narration: Generated narration voiceover text.
        facts: Grounded reference facts.
        project_id: Project UUID string.
    """
    return governance_agent.audit_scene(visual_prompt, narration, facts or [], project_id)

def delegate_publishing_gates_task(project_id: str) -> Dict[str, Any]:
    """
    Delegates verification of 7 fail-closed publishing gates to PublishingAgent (ADK A2A handoff).
    
    Args:
        project_id: Project UUID string.
    """
    return publishing_agent.verify_readiness(project_id)
