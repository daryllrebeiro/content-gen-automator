import os
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.api.byok import (
    ByokCredentials,
    ByokVerifyRequest,
    is_byok_enforced,
    resolve_gemini_key,
    resolve_video_provider_key,
    verify_gemini_key,
)
from app.services.video_provider_catalog import VideoProviderCatalog


client = TestClient(app)


def test_byok_credentials_properties():
    creds = ByokCredentials(
        gemini_api_key="gem_123",
        runway_api_key="run_456",
        kling_api_key="kling_789",
        elevenlabs_api_key="el_000",
    )
    assert creds.gemini == "gem_123"
    assert creds.runway == "run_456"
    assert creds.kling == "kling_789"
    assert creds.elevenlabs == "el_000"
    assert creds.has_gemini() is True
    assert creds.has_runway() is True
    assert creds.has_kling() is True
    assert creds.has_elevenlabs() is True


def test_is_byok_enforced():
    with patch.dict(os.environ, {"BYOK_ENFORCED": "true"}):
        assert is_byok_enforced() is True

    with patch.dict(os.environ, {"BYOK_ENFORCED": "false", "APP_ENV": "production"}):
        assert is_byok_enforced() is False

    with patch.dict(os.environ, {"BYOK_ENFORCED": "", "APP_ENV": "production"}):
        assert is_byok_enforced() is True

    with patch.dict(os.environ, {"BYOK_ENFORCED": "", "APP_ENV": "development"}):
        assert is_byok_enforced() is False


def test_resolve_gemini_key_enforced_vs_dev():
    creds_with_key = ByokCredentials(gemini_api_key="user_key_abc")
    creds_empty = ByokCredentials()

    # When user passes key, it's always used
    with patch.dict(os.environ, {"BYOK_ENFORCED": "true", "GEMINI_API_KEY": "server_secret"}):
        assert resolve_gemini_key(creds_with_key) == "user_key_abc"
        # Enforced mode: Server secret must NEVER leak to anonymous user
        assert resolve_gemini_key(creds_empty) is None

    # Development mode: falls back to server env
    with patch.dict(os.environ, {"BYOK_ENFORCED": "false", "GEMINI_API_KEY": "server_secret"}):
        assert resolve_gemini_key(creds_empty) == "server_secret"


def test_resolve_video_provider_key():
    creds = ByokCredentials(runway_api_key="run_key", kling_api_key="kling_key")
    assert resolve_video_provider_key("mock", creds) == "mock_key"
    assert resolve_video_provider_key("runway", creds) == "run_key"
    assert resolve_video_provider_key("kling", creds) == "kling_key"

    empty_creds = ByokCredentials()
    with patch.dict(os.environ, {"BYOK_ENFORCED": "true"}):
        assert resolve_video_provider_key("runway", empty_creds) is None
        assert resolve_video_provider_key("kling", empty_creds) is None


def test_verify_gemini_key_mock():
    assert verify_gemini_key("")["valid"] is False
    assert verify_gemini_key("   ")["valid"] is False
    mock_res = verify_gemini_key("mock_test_key")
    assert mock_res["valid"] is True
    assert mock_res["provider"] == "gemini"


def test_verify_byok_endpoint():
    res = client.post("/api/byok/verify", json={"provider": "gemini", "api_key": "mock_test_key"})
    assert res.status_code == 200
    assert res.json()["valid"] is True

    # Empty key returns 400
    res_bad = client.post("/api/byok/verify", json={"provider": "gemini", "api_key": ""})
    assert res_bad.status_code == 400


def test_catalog_video_providers_with_byok_headers():
    # Without keys in enforced mode
    with patch.dict(os.environ, {"BYOK_ENFORCED": "true"}):
        res = client.get("/api/catalog/video-providers")
        assert res.status_code == 200
        providers = {p["id"]: p for p in res.json()}
        assert providers["mock"]["is_available"] is True
        assert providers["runway"]["is_available"] is False
        assert "BYOK" in providers["runway"]["disabled_reason"]

    # With user Runway header provided
    with patch.dict(os.environ, {"BYOK_ENFORCED": "true"}):
        res = client.get(
            "/api/catalog/video-providers",
            headers={"X-Runway-API-Key": "user_runway_key"}
        )
        assert res.status_code == 200
        providers = {p["id"]: p for p in res.json()}
        assert providers["runway"]["is_available"] is True
