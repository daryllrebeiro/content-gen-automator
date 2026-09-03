from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class StudioPreset:
    id: str
    name: str
    description: str
    target_platforms: List[str]
    video_provider: str
    model_tier: str
    policy_pack_id: str
    suggested_topic: Optional[str] = None
    suggested_duration: int = 30
    suggested_tone: str = "curious cinematic documentary"
    suggested_style: str = "stylized cinematic 3D animation"
    is_system_preset: bool = True

class StudioPresetService:
    """
    Studio Presets Service.
    Bundles multi-platform target selection, video generation provider, model garden tier,
    and IBM watsonx brand safety policy packs into 1-click reusable director configurations.
    """
    def __init__(self) -> None:
        self._custom_presets: Dict[str, StudioPreset] = {}

    def get_system_presets(self) -> List[StudioPreset]:
        return [
            StudioPreset(
                id="fast_youtube_draft",
                name="⚡ Fast YouTube Draft",
                description="Cost-optimized Gemma draft tier + simulated video for rapid storyboarding.",
                target_platforms=["YOUTUBE_SHORTS"],
                video_provider="mock",
                model_tier="fast_draft",
                policy_pack_id="general_audience",
                suggested_topic="The Hidden World of Bioluminescent Deep Sea Creatures",
                suggested_duration=30,
                suggested_tone="curious cinematic documentary",
                suggested_style="hyper-detailed 4K bioluminescent underwater 3D animation"
            ),
            StudioPreset(
                id="multi_platform_viral",
                name="🚀 Multi-Platform Viral Launch",
                description="Simultaneous fan-out across YouTube Shorts, TikTok, and Instagram Reels with Flagship reasoning.",
                target_platforms=["YOUTUBE_SHORTS", "TIKTOK", "INSTAGRAM_REELS"],
                video_provider="runway",
                model_tier="flagship",
                policy_pack_id="general_audience",
                suggested_topic="Quantum Computing Breakthroughs in 2026",
                suggested_duration=30,
                suggested_tone="authoritative tech documentary",
                suggested_style="sleek corporate cyberpunk 3D motion graphics with glowing circuitry"
            ),
            StudioPreset(
                id="enterprise_compliance_launch",
                name="🛡️ Enterprise Safe Launch",
                description="Strict Kids & Family brand safety rules with Gemini Omni Flash prompt adherence.",
                target_platforms=["YOUTUBE_SHORTS", "INSTAGRAM_REELS"],
                video_provider="gemini_omni",
                model_tier="flagship",
                policy_pack_id="kids_family",
                suggested_topic="The Ancient Secrets of Rainforest Canopies",
                suggested_duration=30,
                suggested_tone="educational and inspiring",
                suggested_style="warm atmospheric nature documentary"
            ),
        ]

    def list_presets(self) -> List[Dict[str, Any]]:
        all_presets = self.get_system_presets() + list(self._custom_presets.values())
        return [p.__dict__ for p in all_presets]

    def get_preset(self, preset_id: str) -> Optional[StudioPreset]:
        for p in self.get_system_presets():
            if p.id == preset_id:
                return p
        return self._custom_presets.get(preset_id)

    def create_custom_preset(self, data: Dict[str, Any]) -> StudioPreset:
        preset = StudioPreset(
            id=data.get("id") or f"custom_{len(self._custom_presets) + 1}",
            name=data["name"],
            description=data.get("description", "Custom Director Studio Preset"),
            target_platforms=data.get("target_platforms", ["YOUTUBE_SHORTS"]),
            video_provider=data.get("video_provider", "mock"),
            model_tier=data.get("model_tier", "flagship"),
            policy_pack_id=data.get("policy_pack_id", "general_audience"),
            suggested_topic=data.get("suggested_topic"),
            suggested_duration=data.get("suggested_duration", 30),
            suggested_tone=data.get("suggested_tone", "curious cinematic documentary"),
            suggested_style=data.get("suggested_style", "stylized cinematic 3D animation"),
            is_system_preset=False
        )
        self._custom_presets[preset.id] = preset
        return preset

studio_preset_service = StudioPresetService()
