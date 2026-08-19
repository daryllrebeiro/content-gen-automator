import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

class YouTubePublishService:
    def __init__(self) -> None:
        # Load OAuth2 credentials from environment variables
        self.client_id = os.environ.get("YOUTUBE_CLIENT_ID")
        self.client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
        self.refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

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
