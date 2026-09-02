from typing import Dict, Any, List
from google.adk.agents import LlmAgent
from app.agents.tools.publishing_tools import check_publishing_gates_tool

class PublishingAgent(LlmAgent):
    """
    ADK Sub-Agent: Publishing Gate & YouTube Distribution Specialist.
    Executes 7 fail-closed gates, verifies compliance certificates, and schedules YouTube releases.
    """
    role: str = "Publishing Gates & Distribution Officer"

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


publishing_agent = PublishingAgent(
    name="publishing_agent",
    model="gemini-2.5-flash",
    instruction="Verify all 7 fail-closed publishing gates and certify compliance before distribution.",
    tools=[check_publishing_gates_tool]
)
