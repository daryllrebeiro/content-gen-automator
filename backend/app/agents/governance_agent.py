from typing import Dict, Any, List
from app.agents.tools.governance_tools import watsonx_audit_prompt_tool, watsonx_audit_narration_tool

class GovernanceAgent:
    """
    ADK Sub-Agent: IBM watsonx Compliance & Safety Specialist.
    Audits visual prompts and narration scripts for brand safety, copyright risks, and hallucinations.
    """
    def __init__(self, model_name: str = "gemini-3.7-flash"):
        self.model_name = model_name
        self.role = "IBM watsonx Governance & Safety Officer"
        self.tools = [watsonx_audit_prompt_tool, watsonx_audit_narration_tool]

    def audit_scene(self, visual_prompt: str, narration: str, facts: List[str] = None, project_id: str = "") -> Dict[str, Any]:
        """
        Executes comprehensive dual-pass governance audit (visual + narration).
        """
        prompt_audit = watsonx_audit_prompt_tool(visual_prompt, project_id=project_id)
        narration_audit = watsonx_audit_narration_tool(narration, facts or [], project_id=project_id)

        overall_passed = (prompt_audit.get("decision") == "passed" and narration_audit.get("decision") == "passed")
        combined_risk = max(prompt_audit.get("risk_score", 0.0), narration_audit.get("risk_score", 0.0))

        return {
            "agent": "GovernanceAgent",
            "decision": "passed" if overall_passed else "flagged",
            "risk_score": combined_risk,
            "prompt_audit": prompt_audit,
            "narration_audit": narration_audit,
            "governance_standard": "IBM watsonx Enterprise Media Standard"
        }


governance_agent = GovernanceAgent()
