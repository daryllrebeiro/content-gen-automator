import os
from typing import Optional


class YouTubePublishService:
    def __init__(self) -> None:
        # Load OAuth2 credentials from environment variables
        self.client_id = os.environ.get("YOUTUBE_CLIENT_ID")
        self.client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
        self.refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    @staticmethod
    def validate_metadata(
        title: str,
        description: str = "",
        tags: list[str] | None = None,
        thumbnail_url: str | None = None,
        thumbnail_path: str | None = None,
    ) -> tuple[bool, list[str], list[str]]:
        """Validate metadata against YouTube Shorts technical specifications."""
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Title validation
        if not title or not title.strip():
            errors.append("Title is required and cannot be blank.")
        elif len(title) > 100:
            errors.append(f"Title exceeds maximum permitted length of 100 characters (got {len(title)}).")
        elif any(ord(c) < 32 and c not in "\t\n\r" for c in title):
            errors.append("Title contains illegal control characters.")

        if title and not any(tag in title.lower() for tag in ("#shorts", "#short")):
            warnings.append("Title does not contain '#Shorts' hashtag, which is recommended for vertical Shorts indexing.")

        # 2. Description validation
        if len(description) > 5000:
            errors.append(f"Description exceeds maximum permitted length of 5000 characters (got {len(description)}).")

        # 3. Tags validation
        tag_list = tags or []
        combined_tag_len = sum(len(t) for t in tag_list)
        if combined_tag_len > 500:
            errors.append(f"Combined tag length exceeds 500 characters (got {combined_tag_len}).")
        for tag in tag_list:
            if len(tag) > 100:
                errors.append(f"Individual tag '{tag[:20]}...' exceeds 100 characters.")

        # 4. Thumbnail validation
        if thumbnail_path:
            if not os.path.exists(thumbnail_path):
                errors.append(f"Specified thumbnail file does not exist: {thumbnail_path}")
            else:
                size_mb = os.path.getsize(thumbnail_path) / (1024 * 1024)
                if size_mb > 2.0:
                    errors.append(f"Thumbnail file size ({size_mb:.2f}MB) exceeds 2MB limit.")
                ext = os.path.splitext(thumbnail_path)[1].lower()
                if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                    errors.append(f"Thumbnail extension '{ext}' not supported. Must be JPG, PNG, or WebP.")

        if thumbnail_url and not thumbnail_url.startswith(("http://", "https://")):
            errors.append("Thumbnail URL must begin with http:// or https://")

        return (len(errors) == 0, errors, warnings)

    def publish_shorts(self, project, video_path: str) -> str:
        """Uploads the stitched video file to YouTube as a vertical Short.

        Throws configuration error if OAuth2 credentials are not set.
        """
        if not (self.client_id and self.client_secret and self.refresh_token):
            raise ValueError(
                "YouTube OAuth2 credentials (YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, "
                "YOUTUBE_REFRESH_TOKEN) are not configured. "
                "Set publish_provider to 'mock' or configure OAuth credentials."
            )

        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from google.oauth2.credentials import Credentials
        except ImportError:
            raise RuntimeError("google-api-python-client and google-auth are required for live YouTube uploads.")

        # Build credentials object
        creds = Credentials(
            token=None,
            refresh_token=self.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret
        )

        youtube = build("youtube", "v3", credentials=creds)

        # Extract title and description
        title = f"{project.input.topic} — Short Documentary"
        if len(title) > 95:
            title = title[:95]
        description = f"{project.story_hook}\n\n{project.story_ending}\n\n#Shorts #YouTubeShorts"

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["Shorts", "YouTubeShorts", "Documentary", "Animation"],
                "categoryId": "27"  # Education
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(
            video_path,
            chunksize=-1,
            resumable=True,
            mimetype="video/mp4"
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = request.execute()
        video_id = response.get("id")
        if not video_id:
            raise RuntimeError("YouTube upload succeeded but no video ID was returned.")

        return f"https://youtu.be/{video_id}"

    def unpublish_video(self, video_id: str) -> dict[str, str]:
        """Rollback: Sets a YouTube video to private or removes it."""
        if not (self.client_id and self.client_secret and self.refresh_token):
            # In mock/sandbox mode, acknowledge rollback
            return {"status": "UNPUBLISHED", "video_id": video_id, "mode": "sandbox"}

        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials

            creds = Credentials(
                token=None,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            youtube = build("youtube", "v3", credentials=creds)
            # Update status to private
            youtube.videos().update(
                part="status",
                body={"id": video_id, "status": {"privacyStatus": "private"}}
            ).execute()
            return {"status": "UNPUBLISHED", "video_id": video_id, "mode": "oauth2_private"}
        except Exception as e:
            raise RuntimeError(f"Failed to unpublish YouTube video {video_id}: {e}")
