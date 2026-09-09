import json
import os
import time
from typing import Any, Callable

from app.domain.facts import FactClaim, FactStatus


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
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

    def _call_with_fallback(self, func: Callable[[str], Any]) -> Any:
        models_to_try = [self.model]
        for alt in ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-2.0-flash"]:
            if alt not in models_to_try:
                models_to_try.append(alt)

        last_error = None
        for m in models_to_try:
            for attempt in range(1, 3):
                try:
                    return func(m)
                except Exception as exc:
                    err_str = str(exc)
                    last_error = exc
                    if any(k in err_str for k in ("503", "UNAVAILABLE", "high demand", "RESOURCE_EXHAUSTED", "429")):
                        time.sleep(1.0 * attempt)
                        continue
                    raise exc
        if last_error:
            raise last_error
        raise RuntimeError("Gemini call failed with no error returned.")

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        def _invoke(model_name: str) -> dict[str, Any]:
            response = self.client.models.generate_content(
                model=model_name,
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

        return self._call_with_fallback(_invoke)

    def verify_claim(self, claim: FactClaim, source_urls: list[str]) -> FactClaim:
        """Verify one claim with Google Search grounding and return cited evidence."""
        def _invoke(model_name: str) -> FactClaim:
            target_model = os.environ.get("GEMINI_FACT_MODEL", model_name)
            response = self.client.models.generate_content(
                model=target_model,
                contents=(
                    "Verify the following factual claim for a documentary short. Search the web, "
                    "prefer authoritative primary sources, and do not infer missing details.\n\n"
                    f"Claim: {claim.text}\nUser-supplied URLs: {source_urls}\n\n"
                    "Return JSON with status, confidence from 0 to 1, source URLs, and notes."
                ),
                config=self._types.GenerateContentConfig(
                    tools=[self._types.Tool(google_search=self._types.GoogleSearch())],
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["verified", "partially_verified", "uncertain", "contradicted"]},
                            "confidence": {"type": "number"},
                            "sources": {"type": "array", "items": {"type": "string"}},
                            "notes": {"type": "string"},
                        },
                        "required": ["status", "confidence", "sources", "notes"],
                    },
                ),
            )
            if not response.text:
                raise RuntimeError("Gemini returned no fact verification result.")
            result = json.loads(response.text)
            return FactClaim(
                id=claim.id,
                text=claim.text,
                status=FactStatus(result["status"]),
                confidence=max(0.0, min(1.0, float(result["confidence"]))),
                sources=result.get("sources", []) or source_urls,
                notes=result.get("notes", ""),
            )

        return self._call_with_fallback(_invoke)
