from typing import Dict, Any, List
from app.agents.tools.publishing_tools import check_publishing_gates_tool

class PublishingAgent:
    """
    ADK Sub-Agent: Publishing Gate & YouTube Distribution Specialist.
    Executes 7 fail-closed gates, verifies compliance certificates, and schedules YouTube releases.
    """
    def __init__(self, model_name: str = "gemini-3.7-flash"):
        self.model_name = model_name
        self.role = "Publishing Gates & Distribution Officer"
        self.tools = [check_publishing_gates_tool]

    def verify_readiness(self, project_id: str) -> Dict[str, Any]:
        """
        Runs gate checklist to confirm if project can be legally and technically published.
        """
        gates = check_publishing_gates_tool(project_id)
        return {
            "agent": "PublishingAgent",
            "can_publish": gates["can_publish"],
            "failed_gates": gates["failed_gates"],
            "gate_summary": f"{gates['gate_count_passed']}/7 Gates Passed"
        }


publishing_agent = PublishingAgent()
