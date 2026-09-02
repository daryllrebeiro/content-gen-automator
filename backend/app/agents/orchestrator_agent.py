from typing import Dict, Any, List, Optional
from google.adk.agents import LlmAgent
from app.agents.research_agent import research_agent
from app.agents.screenwriter_agent import screenwriter_agent
from app.agents.cinematographer_agent import cinematographer_agent
from app.agents.continuity_agent import continuity_agent
from app.agents.governance_agent import governance_agent
from app.agents.publishing_agent import publishing_agent
from app.agents.tools.orchestrator_tools import (
    delegate_research_task,
    delegate_screenplay_task,
    delegate_cinematography_task,
    delegate_continuity_lock_task,
    delegate_governance_audit_task,
    delegate_publishing_gates_task
)

class OrchestratorAgent(LlmAgent):
    """
    ADK Root Agent: Studio Director & Executive Producer.
    Orchestrates the entire multi-agent hierarchy using Agent2Agent (A2A) handoffs,
    synthesizing research, writing, cinematography, governance, and distribution.
    """
    role: str = "Studio Director & Multi-Agent Executive Producer"

    def orchestrate_scene_generation(
        self,
        project_id: str,
        topic: str,
        scene_number: int,
        total_scenes: int,
        tone: str = "curious documentary",
        visual_style: str = "stylized cinematic 3D animation",
        facts: Optional[List[str]] = None,
        studio_id: str = "studio_default"
    ) -> Dict[str, Any]:
        """
        Coordinates full A2A multi-agent sequence for a scene:
        1. ResearchAgent -> Grounding & Facts
        2. ContinuityAgent -> Memory Bank Seed & Brand Voice
        3. ScreenwriterAgent -> Word-Budgeted Narration
        4. CinematographerAgent -> Visual Prompt & Camera Moves
        5. GovernanceAgent -> IBM watsonx Safety Certification
        """
        # 1. Research grounding if facts not provided
        grounded_facts = facts or []
        if not grounded_facts:
            research_res = delegate_research_task(topic, tone)
            grounded_facts = research_res.get("facts", [])

        # 2. Continuity
        continuity = delegate_continuity_lock_task(studio_id, scene_number)

        # 3. Screenplay
        script_res = delegate_screenplay_task(
            topic=topic,
            scene_number=scene_number,
            total_scenes=total_scenes,
            facts=grounded_facts,
            target_seconds=10
        )

        # 4. Cinematography
        visual_res = delegate_cinematography_task(
            scene_number=scene_number,
            topic=topic,
            narration=script_res["narration"],
            visual_style=visual_style,
            continuity_seed=continuity["seed"]
        )

        # 5. Governance Audit
        gov_res = delegate_governance_audit_task(
            visual_prompt=visual_res["visual_prompt"],
            narration=script_res["narration"],
            facts=grounded_facts,
            project_id=project_id
        )

        return {
            "orchestrator": "OrchestratorAgent (google.adk)",
            "project_id": project_id,
            "scene_number": scene_number,
            "narration": script_res["narration"],
            "visual_prompt": visual_res["visual_prompt"],
            "camera_directive": visual_res["camera_directive"],
            "seed": continuity["seed"],
            "governance_decision": gov_res["decision"],
            "risk_score": gov_res["risk_score"],
            "a2a_trace": {
                "research": research_agent.role,
                "screenwriter": screenwriter_agent.role,
                "cinematographer": cinematographer_agent.role,
                "continuity": continuity_agent.role,
                "governance": governance_agent.role
            }
        }


orchestrator_agent = OrchestratorAgent(
    name="orchestrator_agent",
    model="gemini-2.5-flash",
    instruction="Orchestrate the entire cinematic multi-agent pipeline via Agent2Agent (A2A) delegation tools.",
    tools=[
        delegate_research_task,
        delegate_screenplay_task,
        delegate_cinematography_task,
        delegate_continuity_lock_task,
        delegate_governance_audit_task,
        delegate_publishing_gates_task
    ]
)
