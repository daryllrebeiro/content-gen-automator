from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ModelTierSpec:
    id: str  # "fast_draft" | "flagship"
    display_name: str
    screenwriter_model: str
    cinematographer_model: str
    governance_model: str
    estimated_cost_per_draft: float  # in USD
    estimated_latency_ms: float
    description: str

class ModelTierService:
    """
    Model Garden Multi-Tier Selection Service.
    Enables low-cost rapid drafting via lightweight models (Gemma tier) while
    preserving flagship Gemini reasoning for high-stakes cinematography and governance audits.
    """
    TIERS: Dict[str, ModelTierSpec] = {
        "fast_draft": ModelTierSpec(
            id="fast_draft",
            display_name="⚡ Fast Draft (Cost-Optimized Gemma / Flash Tier)",
            screenwriter_model="gemma-2-9b-it",
            cinematographer_model="gemini-2.5-flash",
            governance_model="gemini-2.5-flash",
            estimated_cost_per_draft=0.0002,
            estimated_latency_ms=950.0,
            description="Ultra-fast, low-cost model for rapid screenwriter drafts. Cinematography and IBM governance remain on flagship tier."
        ),
        "flagship": ModelTierSpec(
            id="flagship",
            display_name="👑 Flagship (Gemini 2.5 Flash Reasoning)",
            screenwriter_model="gemini-2.5-flash",
            cinematographer_model="gemini-2.5-flash",
            governance_model="gemini-2.5-flash",
            estimated_cost_per_draft=0.0010,
            estimated_latency_ms=2400.0,
            description="Full-depth reasoning across all agents: Screenwriter, Cinematographer, and Governance Specialist."
        ),
    }

    @classmethod
    def get_tier_spec(cls, tier_id: str) -> ModelTierSpec:
        return cls.TIERS.get(tier_id, cls.TIERS["flagship"])

    @classmethod
    def list_tiers(cls) -> List[Dict[str, Any]]:
        return [
            {
                "id": spec.id,
                "display_name": spec.display_name,
                "screenwriter_model": spec.screenwriter_model,
                "cinematographer_model": spec.cinematographer_model,
                "governance_model": spec.governance_model,
                "estimated_cost_per_draft": f"${spec.estimated_cost_per_draft:.4f}",
                "estimated_latency_ms": f"{spec.estimated_latency_ms:.0f}ms",
                "description": spec.description,
            }
            for spec in cls.TIERS.values()
        ]
