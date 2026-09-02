from typing import Dict, Any, List, Optional
from app.agents.research_agent import research_agent
from app.agents.screenwriter_agent import screenwriter_agent
from app.agents.cinematographer_agent import cinematographer_agent
from app.agents.continuity_agent import continuity_agent
from app.agents.governance_agent import governance_agent
from app.agents.publishing_agent import publishing_agent

class OrchestratorAgent:
    """
    ADK Root Agent: Studio Director & Executive Producer.
    Orchestrates the entire multi-agent hierarchy using Agent2Agent (A2A) handoffs,
    synthesizing research, writing, cinematography, governance, and distribution.
    """
    def __init__(self, model_name: str = "gemini-3.7-flash"):
        self.model_name = model_name
        self.role = "Studio Director & Multi-Agent Executive Producer"
        self.sub_agents = {
            "research": research_agent,
            "screenwriter": screenwriter_agent,
            "cinematographer": cinematographer_agent,
            "continuity": continuity_agent,
            "governance": governance_agent,
            "publishing": publishing_agent,
        }

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
            research_res = self.sub_agents["research"].ground_topic(topic, tone)
            grounded_facts = research_res.get("facts", [])

        # 2. Continuity
        continuity = self.sub_agents["continuity"].get_continuity_lock(studio_id, scene_number)

        # 3. Screenplay
        script_res = self.sub_agents["screenwriter"].draft_narration(
            scene_number=scene_number,
            total_scenes=total_scenes,
            topic=topic,
            facts=grounded_facts,
            target_seconds=10
        )

        # 4. Cinematography
        visual_res = self.sub_agents["cinematographer"].synthesize_visual_prompt(
            scene_number=scene_number,
            topic=topic,
            narration=script_res["narration"],
            visual_style=visual_style,
            continuity_seed=continuity["seed"]
        )

        # 5. Governance Audit
        gov_res = self.sub_agents["governance"].audit_scene(
            visual_prompt=visual_res["visual_prompt"],
            narration=script_res["narration"],
            facts=grounded_facts,
            project_id=project_id
        )

        return {
            "orchestrator": "OrchestratorAgent (ADK)",
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


orchestrator_agent = OrchestratorAgent()
