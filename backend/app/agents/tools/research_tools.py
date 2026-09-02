from typing import Dict, Any, List
from app.adapters.parallel_search import parallel_search
from app.adapters.vertex_search import vertex_search

def parallel_search_tool(topic: str, tone: str = "curious documentary") -> Dict[str, Any]:
    """
    Queries Parallel Search API for verified factual grounding, visual references, and hook ideas.
    
    Args:
        topic: The short topic string.
        tone: The target mood or storytelling tone.
    """
    return parallel_search.research_topic(topic, tone)

def vertex_search_style_tool(query: str) -> Dict[str, Any]:
    """
    Retrieves studio brand guidelines, pacing constraints, and visual rules from Vertex AI Search.
    
    Args:
        query: Query string describing the requested style rules.
    """
    return vertex_search.retrieve_grounding_context(query)
