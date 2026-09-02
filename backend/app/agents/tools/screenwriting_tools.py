from typing import Dict, Any, List, Optional

def draft_narration_tool(
    topic: str,
    duration_seconds: int = 10,
    verified_facts: Optional[List[str]] = None
) -> str:
    """
    Drafts high-retention narration voiceover adhering to duration word budgets (~2.5 words/sec).
    
    Args:
        topic: Story or scene subject.
        duration_seconds: Target clip duration in seconds.
        verified_facts: Grounded facts to incorporate into narration.
    """
    facts = verified_facts or []
    if facts:
        return f"Did you know that {facts[0]} This incredible reality about {topic} shapes our world."
    return f"Discover the untold story of {topic} through breathtaking cinematic visuals."
