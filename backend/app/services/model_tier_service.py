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
    def get_telemetry_metrics(cls, tier_id: str) -> Dict[str, Any]:
        """
        Derives observed telemetry metrics from ClickHouse event records when available,
        falling back to baseline estimated cost/latency.
        """
        spec = cls.get_tier_spec(tier_id)
        from app.adapters.clickhouse_analytics import clickhouse_analytics
        events = [
            e for e in getattr(clickhouse_analytics, "_events", [])
            if e.get("metadata", {}).get("model_tier") == tier_id
        ]
        if events:
            durations = [e.get("duration_ms", 0.0) for e in events if e.get("duration_ms", 0.0) > 0]
            avg_duration = sum(durations) / len(durations) if durations else spec.estimated_latency_ms
            return {
                "is_observed_telemetry": True,
                "sample_count": len(events),
                "cost_per_draft": spec.estimated_cost_per_draft,
                "latency_ms": round(avg_duration, 1),
                "metric_type": "ClickHouse Observed Telemetry"
            }
        return {
            "is_observed_telemetry": False,
            "sample_count": 0,
            "cost_per_draft": spec.estimated_cost_per_draft,
            "latency_ms": spec.estimated_latency_ms,
            "metric_type": "Estimated Baseline Model Rate"
        }

    @classmethod
    def list_tiers(cls) -> List[Dict[str, Any]]:
        result = []
        for spec in cls.TIERS.values():
            telemetry_data = cls.get_telemetry_metrics(spec.id)
            result.append({
                "id": spec.id,
                "display_name": spec.display_name,
                "screenwriter_model": spec.screenwriter_model,
                "cinematographer_model": spec.cinematographer_model,
                "governance_model": spec.governance_model,
                "estimated_cost_per_draft": f"${telemetry_data['cost_per_draft']:.4f}",
                "estimated_latency_ms": f"{telemetry_data['latency_ms']:.0f}ms",
                "is_observed_telemetry": telemetry_data["is_observed_telemetry"],
                "metric_type": telemetry_data["metric_type"],
                "description": spec.description,
            })
        return result
