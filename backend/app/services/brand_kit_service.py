from typing import Dict, List, Any, Optional
from pydantic import BaseModel

class BrandKit(BaseModel):
    studio_id: str
    studio_name: str
    logo_url: str = "/static/branding/default_logo.png"
    watermark_opacity: float = 0.85
    watermark_position: str = "top_right" # "top_right", "bottom_right", "top_left"
    intro_bumper_url: Optional[str] = None
    outro_bumper_url: Optional[str] = None
    default_aspect_ratio: str = "9:16" # "9:16", "1:1", "16:9"

class BrandKitService:
    """
    Brand Kit & Watermark Overlay Service.
    Applies studio branding assets, watermarks, and bumpers into FFmpeg assembly rules.
    """
    def __init__(self):
        self._kits: Dict[str, BrandKit] = {
            "studio_default": BrandKit(
                studio_id="studio_default",
                studio_name="Agentic Cinema Studio",
                logo_url="/static/branding/studio_logo.png",
                watermark_opacity=0.8,
                watermark_position="top_right"
            )
        }

    def get_brand_kit(self, studio_id: str = "studio_default") -> BrandKit:
        return self._kits.get(studio_id, self._kits["studio_default"])

    def register_brand_kit(self, kit: BrandKit) -> BrandKit:
        self._kits[kit.studio_id] = kit
        return kit


brand_kit_service = BrandKitService()
