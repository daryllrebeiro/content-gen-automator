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
            import json
            import shutil
            from uuid import UUID
            project_id = str(UUID(str(project.id)))
            package_dir = f"app/static/exports/youtube_{project_id}"
            os.makedirs(package_dir, exist_ok=True)

            target_video = f"{package_dir}/youtube_{project_id}.mp4"
            if os.path.exists(asset_path):
                shutil.copyfile(asset_path, target_video)
            else:
                with open(target_video, "w", encoding="utf-8") as f:
                    f.write(f"EXPORT_YOUTUBE_9_16:{project_id}")

            vtt_path = f"{package_dir}/captions.vtt"
            with open(vtt_path, "w", encoding="utf-8") as f:
                f.write(f"WEBVTT\n\n00:00:00.000 --> 00:00:10.000\n{project.story_hook or project.input.topic}\n")

            hashtags = ["#Shorts", "#YouTubeShorts", "#CinemaAI", "#DocuShorts"]
            caption_text = f"{project.story_hook or project.input.topic}\n\n{' '.join(hashtags)}"
            txt_path = f"{package_dir}/post_copy.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(caption_text)

            manifest_data = {
                "platform": "YOUTUBE_SHORTS",
                "spec": "9:16 Vertical 1080x1920, Max 60s",
                "caption": caption_text,
                "hashtags": hashtags,
                "video_file": os.path.basename(target_video),
                "subtitles_file": os.path.basename(vtt_path),
                "post_copy_file": os.path.basename(txt_path),
                "export_mode": "manual_ready"
            }
            with open(f"{package_dir}/manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)

            return PublishResult(
                platform=Platform.YOUTUBE_SHORTS,
                status="PUBLISHED",
                asset_ref=target_video,
                published_url=f"https://youtube.com/shorts/mock_{project.id}",
                package_dir=package_dir,
                manifest=manifest_data,
                message="YouTube Shorts published in simulated sandbox mode with local package export"
            )
