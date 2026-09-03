from app.domain.project import Platform
from app.services.publish_adapters.base import BasePublishAdapter
from app.services.publish_adapters.youtube_adapter import YouTubePublishAdapter
from app.services.publish_adapters.tiktok_adapter import TikTokPublishAdapter
from app.services.publish_adapters.instagram_adapter import InstagramPublishAdapter

def get_publish_adapter(platform: Platform | str) -> BasePublishAdapter:
    plat_enum = Platform(platform) if isinstance(platform, str) else platform
    if plat_enum == Platform.YOUTUBE_SHORTS:
        return YouTubePublishAdapter()
    elif plat_enum == Platform.TIKTOK:
        return TikTokPublishAdapter()
    elif plat_enum == Platform.INSTAGRAM_REELS:
        return InstagramPublishAdapter()
    else:
        raise ValueError(f"Unsupported publish platform: {platform}")
