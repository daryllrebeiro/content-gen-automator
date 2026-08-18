import json
import os
from typing import Any


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError(
                "Gemini support requires the google-genai package. Install backend requirements."
            ) from exc

        self._types = types
        self.client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        response = self.client.models.generate_content(
            model=self.model,
            contents=f"{system_prompt}\n\n{user_prompt}",
            config=self._types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Gemini returned invalid structured output.") from exc
        if not isinstance(result, dict):
            raise RuntimeError("Gemini structured output must be a JSON object.")
        return result

