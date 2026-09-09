import os
import re
import time
from collections import defaultdict
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from fastapi import Header, HTTPException, status, Request

class SlidingWindowRateLimiter:
    """In-memory rate limiter to prevent /api/byok/verify oracle abuse."""
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - self.window_seconds
        valid_requests = [t for t in self.requests.get(client_id, []) if t > cutoff]
        if not valid_requests:
            self.requests.pop(client_id, None)
            self.requests[client_id] = [now]
            return True, 0
        self.requests[client_id] = valid_requests
        if len(self.requests[client_id]) >= self.max_requests:
            remaining = int(self.window_seconds - (now - self.requests[client_id][0]))
            return False, max(1, remaining)
        self.requests[client_id].append(now)
        return True, 0

verify_rate_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)


def get_trusted_client_ip(request: Request) -> str:
    """Safely extracts client IP address.
    
    Only trusts X-Forwarded-For if the direct peer connection originates from
    a verified local loopback or configured trusted proxy. Otherwise, falls back
    strictly to request.client.host to prevent rate-limiter spoofing.
    """
    peer_ip = request.client.host if request.client else "127.0.0.1"
    trusted_proxies = {"127.0.0.1", "::1", "localhost"}
    env_proxies = os.getenv("TRUSTED_PROXIES", "")
    if env_proxies:
        trusted_proxies.update(p.strip() for p in env_proxies.split(",") if p.strip())

    if peer_ip in trusted_proxies:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
            if client_ip:
                return client_ip

    return peer_ip


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

    def has_any_keys(self) -> bool:
        return bool(
            (self.gemini_api_key and self.gemini_api_key.strip())
            or (self.runway_api_key and self.runway_api_key.strip())
            or (self.kling_api_key and self.kling_api_key.strip())
            or (self.elevenlabs_api_key and self.elevenlabs_api_key.strip())
        )


def is_byok_enforced() -> bool:
    """Returns True if strict BYOK enforcement is explicitly enabled via BYOK_ENFORCED=true.

    In the Hybrid Model (default), anonymous users and evaluators may use the server's
    configured Gemini key up to the FinOps token budget / cost ceiling.
    """
    enforced = os.getenv("BYOK_ENFORCED", "").lower()
    return enforced in ("true", "1", "yes")


def _sanitize_header(value: Optional[str], header_name: str) -> Optional[str]:
    """Validates and sanitizes incoming BYOK header values.
    
    Rejects null bytes, illegal control characters, or oversized strings.
    """
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > 256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "MALFORMED_HEADER",
                "message": f"Header '{header_name}' exceeds maximum permitted length of 256 characters."
            }
        )
    if "\x00" in cleaned or any(ord(c) < 32 or ord(c) == 127 for c in cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "MALFORMED_HEADER",
                "message": f"Header '{header_name}' contains illegal control characters."
            }
        )
    return cleaned


def get_byok_credentials(
    x_gemini_api_key: Optional[str] = Header(default=None, alias="X-Gemini-API-Key"),
    x_runway_api_key: Optional[str] = Header(default=None, alias="X-Runway-API-Key"),
    x_kling_api_key: Optional[str] = Header(default=None, alias="X-Kling-API-Key"),
    x_elevenlabs_api_key: Optional[str] = Header(default=None, alias="X-ElevenLabs-API-Key"),
) -> ByokCredentials:
    """FastAPI Dependency that extracts and validates user-supplied provider API keys."""
    return ByokCredentials(
        gemini_api_key=_sanitize_header(x_gemini_api_key, "X-Gemini-API-Key"),
        runway_api_key=_sanitize_header(x_runway_api_key, "X-Runway-API-Key"),
        kling_api_key=_sanitize_header(x_kling_api_key, "X-Kling-API-Key"),
        elevenlabs_api_key=_sanitize_header(x_elevenlabs_api_key, "X-ElevenLabs-API-Key"),
    )


def resolve_gemini_key(credentials: ByokCredentials) -> Optional[str]:
    """Resolves the Gemini API key to use for the current request.

    If user supplies a key in BYOK headers, always uses that key.
    If BYOK is strictly enforced (BYOK_ENFORCED=true), returns None when no key is supplied.
    In the default Hybrid Model, falls back to the server environment key.
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
    """Validates a user-supplied Gemini API key with Google AI Studio.

    Guarantees:
    - Zero key echo: The submitted API key is never returned in any response field or error message.
    - Pre-validation: Non-matching strings are rejected immediately without external network calls.
    """
    if not api_key or not api_key.strip():
        return {"valid": False, "message": "API key cannot be empty"}

    clean_key = api_key.strip()
    if clean_key.startswith("mock_"):
        return {"valid": True, "provider": "gemini", "model": "mock", "message": "Mock test key verified"}

    # Format verification: Accepts both:
    # 1. Legacy Google standard keys (starting with 'AIza', e.g. AIzaSy... 39 chars)
    # 2. Modern Google AI Studio / Google Cloud Auth keys (starting with 'AQ.')
    is_valid_format = bool(
        re.match(r"^AIza[0-9A-Za-z_-]{30,60}$", clean_key) or
        re.match(r"^AQ\.[0-9A-Za-z_.-]{10,250}$", clean_key)
    )
    if not is_valid_format:
        return {
            "valid": False,
            "provider": "gemini",
            "message": "Invalid Google Gemini API key format. Expected a valid key starting with 'AIza' or 'AQ.'."
        }

    try:
        from google import genai
        client = genai.Client(api_key=clean_key)
        # Attempt a lightweight zero-generation model probe
        models_pager = client.models.list(config={"page_size": 1})
        return {
            "valid": True,
            "provider": "gemini",
            "message": "Key successfully authenticated with Google Gemini API",
        }
    except Exception:
        # Zero-Echo: Never return raw exception details or attempted key back to client
        return {
            "valid": False,
            "provider": "gemini",
            "message": "Google Gemini API key authentication failed. Please verify your key at https://aistudio.google.com/apikey"
        }
