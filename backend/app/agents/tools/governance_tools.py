from typing import Dict, Any, List
from app.adapters.ibm_governance import ibm_governance

def watsonx_audit_prompt_tool(prompt_text: str, visual_style: str = "", project_id: str = "") -> Dict[str, Any]:
    """
    Audits a visual prompt with IBM watsonx.governance guardrails for safety, copyright clearance, and brand compliance.
    
    Args:
        prompt_text: The visual prompt text to inspect.
        visual_style: Visual style preset.
        project_id: Project UUID string.
    """
    return ibm_governance.audit_prompt(prompt_text, visual_style, project_id)

def watsonx_audit_narration_tool(narration_script: str, verified_facts: List[str] = None, project_id: str = "") -> Dict[str, Any]:
    """
    Audits voiceover narration text for factual hallucination risk and PII with IBM watsonx.
    
    Args:
        narration_script: The spoken voiceover text.
        verified_facts: List of ground-truth facts from Parallel Search.
        project_id: Project UUID string.
    """
    return ibm_governance.audit_narration(narration_script, verified_facts or [], project_id)
