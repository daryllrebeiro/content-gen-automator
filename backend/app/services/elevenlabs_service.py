import os
import httpx

class ElevenLabsTTSService:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        # Standard warm documentary voice ID
        self.voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgq5apaqa9W4")

    def synthesize(self, project_id: str, scene_number: int, text: str) -> str:
        """Synthesize text to speech using ElevenLabs API and save to static folder.

        If api_key is missing, fails gracefully by logging a warning and raising config error.
        """
        if not self.api_key:
            raise ValueError(
                "ELEVENLABS_API_KEY is not configured in environment variables. "
                "Set tts_provider to 'mock' or configure the API key."
            )

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
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
