import os
import httpx
from typing import Optional

class ElevenLabsTTSService:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        # Standard warm documentary voice ID
        self.voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgq5apaqa9W4")

    def synthesize(self, project_id: str, scene_number: int, text: str, api_key: Optional[str] = None) -> str:
        """Synthesize text to speech using ElevenLabs API and save to static folder.

        If api_key is missing, fails gracefully with an actionable BYOK error message.
        """
        key = api_key or self.api_key
        if not key:
            raise ValueError(
                "ELEVENLABS_API_KEY is not configured. "
                "Please provide your ElevenLabs API Key in Studio BYOK settings, or set tts_provider to 'mock'."
            )

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {
            "xi-api-key": key,
            "Content-Type": "application/json",
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            }
        }

        response = httpx.post(url, json=data, headers=headers, timeout=30.0)
        if response.status_code != 200:
            raise RuntimeError(
                f"ElevenLabs API failed with status {response.status_code}: {response.text}"
            )

        # Save output to static directory
        dir_path = "app/static/audio"
        os.makedirs(dir_path, exist_ok=True)
        file_path = f"{dir_path}/{project_id}_{scene_number}.mp3"
        with open(file_path, "wb") as f:
            f.write(response.content)

        return file_path
