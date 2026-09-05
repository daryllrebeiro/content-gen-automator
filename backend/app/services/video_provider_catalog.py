import os
from dataclasses import dataclass
from typing import Optional, List, Any

@dataclass
class VideoProviderItem:
    id: str
    name: str
    cost_per_scene: str
    estimated_latency: str
    strengths: str
    is_available: bool
    disabled_reason: Optional[str] = None

class VideoProviderCatalog:
    """
    Modular Video Generation Provider Catalog.
    Exposes real runtime availability, costs, latency expectations, and style strengths.
    Supports Bring Your Own Key (BYOK) dynamic key checking.
    """
    @staticmethod
    def list_providers(byok: Optional[Any] = None) -> List[VideoProviderItem]:
        from app.api.byok import is_byok_enforced
        enforced = is_byok_enforced()

        gemini_key = getattr(byok, "gemini_api_key", None) if byok else None
        if not gemini_key and not enforced:
            gemini_key = os.environ.get("GEMINI_API_KEY")

        runway_key = getattr(byok, "runway_api_key", None) if byok else None
        if not runway_key and not enforced:
            runway_key = os.environ.get("RUNWAYML_API_KEY") or os.environ.get("RUNWAY_API_KEY")

        kling_key = getattr(byok, "kling_api_key", None) if byok else None
        if not kling_key and not enforced:
            kling_key = os.environ.get("KLING_API_KEY")

        return [
            VideoProviderItem(
                id="mock",
                name="Simulated Studio (Mock)",
                cost_per_scene="$0.00 / scene",
                estimated_latency="< 1 sec",
                strengths="Instant zero-cost iteration, ideal for test pipelines and local rehearsals",
                is_available=True,
                disabled_reason=None
            ),
            VideoProviderItem(
                id="gemini_omni",
                name="Google Gemini Omni Flash",
                cost_per_scene="$0.04 / scene",
                estimated_latency="~8-12 sec",
                strengths="Native multimodal prompt adherence, accurate cinematic camera direction",
                is_available=bool(gemini_key and not gemini_key.startswith("mock_")),
                disabled_reason=None if (gemini_key and not gemini_key.startswith("mock_")) else "Requires GEMINI_API_KEY in environment or Studio BYOK settings"
            ),
            VideoProviderItem(
                id="runway",
                name="Runway Gen-3 Alpha",
                cost_per_scene="$0.25 / scene",
                estimated_latency="~35-45 sec",
                strengths="Hyper-realistic atmospheric lighting, cinematic lens distortion, stylized 3D",
                is_available=bool(runway_key and not runway_key.startswith("mock_")),
                disabled_reason=None if (runway_key and not runway_key.startswith("mock_")) else "Requires RUNWAY_API_KEY in environment or Studio BYOK settings"
            ),
            VideoProviderItem(
                id="kling",
                name="Kling AI Video",
                cost_per_scene="$0.10 / scene",
                estimated_latency="~25-30 sec",
                strengths="Fluid character motion coherence, complex physical simulations",
                is_available=bool(kling_key and not kling_key.startswith("mock_")),
                disabled_reason=None if (kling_key and not kling_key.startswith("mock_")) else "Requires KLING_API_KEY in environment or Studio BYOK settings"
            ),
        ]

    @staticmethod
    def get_provider(provider_id: str, byok: Optional[Any] = None) -> Optional[VideoProviderItem]:
        for p in VideoProviderCatalog.list_providers(byok=byok):
            if p.id == provider_id:
                return p
        return None
