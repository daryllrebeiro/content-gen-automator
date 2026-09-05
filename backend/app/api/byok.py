import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import Header, HTTPException, status

class ByokVerifyRequest(BaseModel):
    provider: str = "gemini"
    api_key: str


class ByokCredentials(BaseModel):
    gemini_api_key: Optional[str] = Field(default=None, description="User Google Gemini API Key")
    runway_api_key: Optional[str] = Field(default=None, description="User RunwayML API Key")
    kling_api_key: Optional[str] = Field(default=None, description="User Kling AI API Key")
    elevenlabs_api_key: Optional[str] = Field(default=None, description="User ElevenLabs API Key")

    @property
    def gemini(self) -> Optional[str]:
        return self.gemini_api_key

    @property
    def runway(self) -> Optional[str]:
        return self.runway_api_key

    @property
    def kling(self) -> Optional[str]:
        return self.kling_api_key

    @property
    def elevenlabs(self) -> Optional[str]:
        return self.elevenlabs_api_key

    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.strip() and not self.gemini_api_key.startswith("mock_"))

    def has_runway(self) -> bool:
        return bool(self.runway_api_key and self.runway_api_key.strip())

    def has_kling(self) -> bool:
        return bool(self.kling_api_key and self.kling_api_key.strip())

    def has_elevenlabs(self) -> bool:
        return bool(self.elevenlabs_api_key and self.elevenlabs_api_key.strip())


def is_byok_enforced() -> bool:
    """Returns True if BYOK is strictly enforced (e.g. in production or BYOK_ENFORCED=true).

    In enforced mode, the server's private environment keys are NEVER used for user requests.
    """
    enforced = os.getenv("BYOK_ENFORCED", "").lower()
    if enforced in ("true", "1", "yes"):
        return True
    if enforced in ("false", "0", "no"):
        return False
    # By default, enforce in production so server owner API quota is never drained by public traffic
    return os.getenv("APP_ENV", "development").lower() == "production"


def get_byok_credentials(
    x_gemini_api_key: Optional[str] = Header(default=None, alias="X-Gemini-API-Key"),
    x_runway_api_key: Optional[str] = Header(default=None, alias="X-Runway-API-Key"),
    x_kling_api_key: Optional[str] = Header(default=None, alias="X-Kling-API-Key"),
    x_elevenlabs_api_key: Optional[str] = Header(default=None, alias="X-ElevenLabs-API-Key"),
) -> ByokCredentials:
    """FastAPI Dependency that extracts user-supplied provider API keys from request headers."""
    return ByokCredentials(
        gemini_api_key=x_gemini_api_key.strip() if x_gemini_api_key else None,
        runway_api_key=x_runway_api_key.strip() if x_runway_api_key else None,
        kling_api_key=x_kling_api_key.strip() if x_kling_api_key else None,
        elevenlabs_api_key=x_elevenlabs_api_key.strip() if x_elevenlabs_api_key else None,
    )


def resolve_gemini_key(credentials: ByokCredentials) -> Optional[str]:
    """Resolves the Gemini API key to use for the current request.

    If BYOK is enforced, strictly returns the user's key (or None).
    Only falls back to the server environment key in local development/testing.
    """
    if credentials.gemini_api_key and credentials.gemini_api_key.strip():
        return credentials.gemini_api_key.strip()
    if is_byok_enforced():
        return None
    server_key = os.getenv("GEMINI_API_KEY", "").strip()
    return server_key if server_key else None


def require_gemini_key(credentials: ByokCredentials, provider_name: str = "Google Gemini") -> str:
    """Resolves Gemini key or raises HTTP 400 instructing the user to configure BYOK."""
    key = resolve_gemini_key(credentials)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "BYOK_KEY_REQUIRED",
                "provider": "gemini",
                "message": (
                    f"You selected {provider_name}, but have not provided your Gemini API Key. "
                    "This deployment is in Bring-Your-Own-Key (BYOK) mode. "
                    "Please click '🔑 API Keys' in the studio header to set your Gemini API key, "
                    "or select 'Simulated Studio (Mock)' to test for free without a key."
                ),
                "action_url": "https://aistudio.google.com/apikey"
            }
        )
    return key


def resolve_video_provider_key(provider_id: str, credentials: ByokCredentials) -> Optional[str]:
    """Resolves the key for a specific video provider."""
    if provider_id == "mock":
        return "mock_key"
    if provider_id == "gemini_omni":
        return resolve_gemini_key(credentials)
    if provider_id == "runway":
        if credentials.runway_api_key:
            return credentials.runway_api_key
        return None if is_byok_enforced() else (os.getenv("RUNWAYML_API_KEY") or os.getenv("RUNWAY_API_KEY"))
    if provider_id == "kling":
        if credentials.kling_api_key:
            return credentials.kling_api_key
        return None if is_byok_enforced() else os.getenv("KLING_API_KEY")
    return None


def verify_gemini_key(api_key: str) -> Dict[str, Any]:
    """Validates a user-supplied Gemini API key with Google AI Studio."""
    if not api_key or not api_key.strip():
        return {"valid": False, "message": "API key cannot be empty"}

    clean_key = api_key.strip()
    if clean_key.startswith("mock_"):
        return {"valid": True, "provider": "gemini", "model": "mock", "message": "Mock test key verified"}

    try:
        from google import genai
        client = genai.Client(api_key=clean_key)
        # Attempt a lightweight operation to verify authentication
        # Listing 1 model is fast and free of generation charges
        models_pager = client.models.list(config={"page_size": 1})
        # If we reach here without 401/403, key is authentic
        return {
            "valid": True,
            "provider": "gemini",
            "message": "Key successfully authenticated with Google Gemini API",
        }
    except Exception as exc:
        err_msg = str(exc)
        if "400" in err_msg or "401" in err_msg or "403" in err_msg or "API_KEY_INVALID" in err_msg:
            return {
                "valid": False,
                "provider": "gemini",
                "message": "Invalid Google Gemini API key. Please check the key in Google AI Studio."
            }
        return {
            "valid": False,
            "provider": "gemini",
            "message": f"Verification error: {err_msg[:120]}"
        }
