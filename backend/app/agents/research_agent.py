from typing import Dict, Any, List
from app.agents.tools.research_tools import parallel_search_tool, vertex_search_style_tool

class ResearchAgent:
    """
    ADK Sub-Agent: Research & Grounding Specialist.
    Conducts agentic web research via Parallel Search and style guide retrieval via Vertex AI Search.
    """
    def __init__(self, model_name: str = "gemini-3.7-flash"):
        self.model_name = model_name
        self.role = "Research & Factual Grounding Specialist"
        self.tools = [parallel_search_tool, vertex_search_style_tool]

    def ground_topic(self, topic: str, tone: str = "curious documentary") -> Dict[str, Any]:
        """
        Executes research tool to ground topic in verified facts and visual keywords.
        """
        parallel_data = parallel_search_tool(topic, tone)
        style_data = vertex_search_style_tool(topic)
        return {
            "agent": "ResearchAgent",
            "topic": topic,
            "facts": parallel_data.get("verified_facts", []),
            "visual_references": parallel_data.get("visual_references", []),
            "audience_hook": parallel_data.get("audience_hook", ""),
            "guidelines": style_data.get("matched_guidelines", []),
        }


research_agent = ResearchAgent()
