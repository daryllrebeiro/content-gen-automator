import os
from app.domain.project import Project, Platform
from app.services.publish_adapters.base import BasePublishAdapter, PublishResult
from app.services.youtube_publish_service import YouTubePublishService

class YouTubePublishAdapter(BasePublishAdapter):
    def __init__(self) -> None:
        self.service = YouTubePublishService()

    def publish(self, project: Project, asset_path: str) -> PublishResult:
        if self.service.client_id and self.service.client_secret and self.service.refresh_token:
            video_id = self.service.publish_shorts(project, asset_path)
            url = f"https://youtube.com/shorts/{video_id}"
            return PublishResult(
                platform=Platform.YOUTUBE_SHORTS,
                status="PUBLISHED",
                asset_ref=asset_path,
                published_url=url,
                message="Successfully uploaded to YouTube Shorts via OAuth2 API"
            )
        else:
            return PublishResult(
                platform=Platform.YOUTUBE_SHORTS,
                status="PUBLISHED",
                asset_ref=asset_path,
                published_url=f"https://youtube.com/shorts/mock_{project.id}",
                message="YouTube Shorts published in simulated sandbox mode"
            )
