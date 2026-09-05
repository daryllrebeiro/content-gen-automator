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
    verify_rate_limiter,
)
from app.services.video_provider_catalog import VideoProviderCatalog
from app.adapters.grafana_telemetry import telemetry


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

    with patch.dict(os.environ, {"BYOK_ENFORCED": "1"}):
        assert is_byok_enforced() is True

    with patch.dict(os.environ, {"BYOK_ENFORCED": "false"}):
        assert is_byok_enforced() is False

    # Hybrid Model: When BYOK_ENFORCED is unset in production, defaults to Hybrid (False)
    with patch.dict(os.environ, {"BYOK_ENFORCED": "", "APP_ENV": "production"}):
        assert is_byok_enforced() is False


def test_resolve_gemini_key_enforced_vs_dev():
    creds_with_key = ByokCredentials(gemini_api_key="user_key_abc")
    creds_empty = ByokCredentials()

    # When user passes key, it's always used
    with patch.dict(os.environ, {"BYOK_ENFORCED": "true", "GEMINI_API_KEY": "server_secret"}):
        assert resolve_gemini_key(creds_with_key) == "user_key_abc"
        # Strict enforced mode: Server secret must NEVER leak to anonymous user
        assert resolve_gemini_key(creds_empty) is None

    # Hybrid / Development mode: falls back to server env up to cost ceiling
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


def test_verify_gemini_key_mock_and_validation():
    assert verify_gemini_key("")["valid"] is False
    assert verify_gemini_key("   ")["valid"] is False
    
    # Pre-validation: rejects non-AIzaSy format immediately without external network calls
    invalid_format = verify_gemini_key("not_a_real_key_123")
    assert invalid_format["valid"] is False
    assert "Invalid Google Gemini API key format" in invalid_format["message"]
    
    # Mock key bypass for testing
    mock_res = verify_gemini_key("mock_test_key")
    assert mock_res["valid"] is True
    assert mock_res["provider"] == "gemini"


def test_zero_key_echo():
    secret_candidate = "AIzaSySecretCandidateKeyThatMustNeverEcho12"
    res = client.post("/api/byok/verify", json={"provider": "gemini", "api_key": secret_candidate})
    # Body must NEVER contain the submitted key value
    body_text = res.text
    assert secret_candidate not in body_text


def test_malformed_header_rejection():
    # 1. Oversized header (> 256 chars)
    oversized = "A" * 300
    res = client.get("/api/catalog/video-providers", headers={"X-Gemini-API-Key": oversized})
    assert res.status_code == 400
    assert "exceeds maximum permitted length" in res.json()["detail"]["message"]

    # 2. Control characters / null byte rejection
    null_byte = "key\x00attack"
    res2 = client.get("/api/catalog/video-providers", headers={"X-Gemini-API-Key": null_byte})
    assert res2.status_code == 400
    assert "illegal control characters" in res2.json()["detail"]["message"]


def test_verify_byok_rate_limiting():
    # Reset limiter for test client
    verify_rate_limiter.requests.clear()

    # First 10 calls should succeed
    for i in range(10):
        res = client.post("/api/byok/verify", json={"provider": "gemini", "api_key": "mock_test_key"})
        assert res.status_code == 200

    # 11th call must be blocked with HTTP 429 Too Many Requests
    res_blocked = client.post("/api/byok/verify", json={"provider": "gemini", "api_key": "mock_test_key"})
    assert res_blocked.status_code == 429
    assert res_blocked.json()["detail"]["error"] == "RATE_LIMIT_EXCEEDED"

    # Reset limiter so other tests are not impacted
    verify_rate_limiter.requests.clear()


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


def test_hybrid_model_cost_ceiling_enforcement():
    # Create test project
    res = client.post("/api/projects", json={
        "topic": "Quantum Teleportation",
        "duration_seconds": 10,
        "tts_provider": "mock",
        "video_provider": "mock"
    })
    assert res.status_code == 200
    proj_id = res.json()["id"]

    # 1. Anonymous request within budget generates successfully
    res_gen = client.post(f"/api/projects/{proj_id}/prompts/next")
    assert res_gen.status_code == 200

    # 2. Simulate token budget exhaustion on this project
    telemetry.project_tokens[proj_id] = 60000  # Exceeds 50,000 ceiling

    # Anonymous request should now be blocked with HTTP 429 (COST_CEILING_EXCEEDED)
    with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "mock_server_key"}):
        res_blocked = client.post(f"/api/projects/{proj_id}/prompts/next")
        assert res_blocked.status_code == 429
        assert res_blocked.json()["detail"]["error"] == "COST_CEILING_EXCEEDED"
        assert "Free evaluation token budget reached" in res_blocked.json()["detail"]["message"]

        # 3. User providing their OWN BYOK key bypasses the server cost ceiling!
        res_byok = client.post(
            f"/api/projects/{proj_id}/prompts/next",
            headers={"X-Gemini-API-Key": "mock_user_personal_key"}
        )
        assert res_byok.status_code == 200
