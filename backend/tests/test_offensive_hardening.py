import os
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from fastapi import Request
from app.main import app
from app.services.ffmpeg_service import FFmpegAssemblyService, DEFAULT_FFMPEG_TIMEOUT
from app.api.byok import get_trusted_client_ip
from app.api.routes import project_creation_limiter
from app.config import Settings

client = TestClient(app)


def test_mock_complete_production_cross_project_rejected_404():
    """OFF-01: Verify that completing another project's production job is rejected with 404."""
    # 1. Create Project A (Attacker)
    res_a = client.post("/api/projects", json={"topic": "Tenant A Project", "duration_seconds": 10})
    assert res_a.status_code == 200
    p_a_id = res_a.json()["id"]
    token_a = res_a.json()["owner_token"]

    # 2. Create Project B (Victim)
    res_b = client.post("/api/projects", json={"topic": "Tenant B Project", "duration_seconds": 10})
    assert res_b.status_code == 200
    p_b_id = res_b.json()["id"]
    token_b = res_b.json()["owner_token"]

    # 3. Setup Project B: generate, approve, submit production
    client.post(f"/api/projects/{p_b_id}/generate", headers={"X-Project-Owner-Token": token_b})
    client.post(
        f"/api/projects/{p_b_id}/prompts/1/approve",
        json={"actor": "victim"},
        headers={"X-Project-Owner-Token": token_b, "X-Expected-Version": "2"}
    )
    prod_b = client.post(
        f"/api/projects/{p_b_id}/scenes/1/production",
        headers={"X-Project-Owner-Token": token_b, "Idempotency-Key": f"test-prod-off01-{p_b_id}"}
    )
    assert prod_b.status_code == 200
    job_b_id = prod_b.json()["job_id"]

    # 4. Attacker A attempts to mock-complete Victim B's job under Project A URL
    attack_res = client.post(
        f"/api/projects/{p_a_id}/production-jobs/{job_b_id}/mock-complete",
        headers={"X-Project-Owner-Token": token_a}
    )
    assert attack_res.status_code == 404
    assert "Production job not found for this project" in attack_res.json()["detail"]


def test_mock_complete_youtube_cross_project_rejected_404():
    """OFF-01: Verify that completing another project's YouTube job is rejected with 404."""
    # 1. Create Project A (Attacker)
    res_a = client.post("/api/projects", json={"topic": "Tenant A YT Project", "duration_seconds": 10})
    p_a_id = res_a.json()["id"]
    token_a = res_a.json()["owner_token"]

    # 2. Create Project B (Victim)
    res_b = client.post("/api/projects", json={"topic": "Tenant B YT Project", "duration_seconds": 10})
    p_b_id = res_b.json()["id"]
    token_b = res_b.json()["owner_token"]

    client.post(f"/api/projects/{p_b_id}/generate", headers={"X-Project-Owner-Token": token_b})
    client.post(
        f"/api/projects/{p_b_id}/prompts/1/approve",
        json={"actor": "victim"},
        headers={"X-Project-Owner-Token": token_b, "X-Expected-Version": "2"}
    )
    prod_b = client.post(
        f"/api/projects/{p_b_id}/scenes/1/production",
        headers={"X-Project-Owner-Token": token_b, "Idempotency-Key": f"test-yt-off01-{p_b_id}"}
    )
    job_b_id = prod_b.json()["job_id"]
    # Complete production for B
    client.post(f"/api/projects/{p_b_id}/production-jobs/{job_b_id}/mock-complete", headers={"X-Project-Owner-Token": token_b})

    # Attacker A creates a fake or references a YouTube upload job
    attack_res = client.post(
        f"/api/projects/{p_a_id}/youtube-upload-jobs/{job_b_id}/mock-complete",
        headers={"X-Project-Owner-Token": token_a}
    )
    assert attack_res.status_code == 404
    assert "YouTube upload job not found for this project" in attack_res.json()["detail"]


def test_clip_review_cross_project_artifact_rejected_404():
    """OFF-02: Verify that reviewing an artifact from another project/scene is rejected."""
    # 1. Project A & Project B
    res_a = client.post("/api/projects", json={"topic": "Tenant A Clip Review", "duration_seconds": 10})
    p_a_id = res_a.json()["id"]
    token_a = res_a.json()["owner_token"]

    res_b = client.post("/api/projects", json={"topic": "Tenant B Clip Review", "duration_seconds": 10})
    p_b_id = res_b.json()["id"]
    token_b = res_b.json()["owner_token"]

    client.post(f"/api/projects/{p_b_id}/generate", headers={"X-Project-Owner-Token": token_b})
    client.post(
        f"/api/projects/{p_b_id}/prompts/1/approve",
        json={"actor": "victim"},
        headers={"X-Project-Owner-Token": token_b, "X-Expected-Version": "2"}
    )
    prod_b = client.post(
        f"/api/projects/{p_b_id}/scenes/1/production",
        headers={"X-Project-Owner-Token": token_b, "Idempotency-Key": f"test-clip-off02-{p_b_id}"}
    )
    job_b_id = prod_b.json()["job_id"]
    
    cb_res = client.post(
        f"/api/integrations/production-jobs/{job_b_id}/callback",
        json={
            "status": "SUCCEEDED",
            "duration_seconds": 10,
            "aspect_ratio": "9:16",
            "narration_end_seconds": 8.5,
            "checksum": "b" * 64,
            "artifact_url": "https://storage.example/victim-clip.mp4",
        }
    )
    artifact_b_id = cb_res.json()["artifact_id"]

    # Attacker A attempts to review Victim B's artifact under Project A
    attack_res = client.post(
        f"/api/projects/{p_a_id}/clips/1/review",
        json={"artifact_id": artifact_b_id, "decision": "rejected", "actor": "attacker"},
        headers={"X-Project-Owner-Token": token_a}
    )
    assert attack_res.status_code == 404
    assert "Clip artifact does not match specified project scene" in attack_res.json()["detail"]


def test_trusted_proxy_client_ip_resolution():
    """OFF-03: Verify that untrusted direct peer IP ignores spoofed X-Forwarded-For."""
    # Scenario A: Untrusted external peer directly sends X-Forwarded-For
    scope_untrusted = {
        "type": "http",
        "client": ("198.51.100.25", 54321),
        "headers": [(b"x-forwarded-for", b"10.0.0.99, 127.0.0.1")],
    }
    req_untrusted = Request(scope_untrusted)
    resolved_ip = get_trusted_client_ip(req_untrusted)
    assert resolved_ip == "198.51.100.25", "Untrusted peer must NOT be allowed to spoof client IP via XFF"

    # Scenario B: Trusted loopback reverse proxy sends X-Forwarded-For
    scope_trusted = {
        "type": "http",
        "client": ("127.0.0.1", 54321),
        "headers": [(b"x-forwarded-for", b"203.0.113.44, 10.0.0.1")],
    }
    req_trusted = Request(scope_trusted)
    resolved_trusted = get_trusted_client_ip(req_trusted)
    assert resolved_trusted == "203.0.113.44", "Trusted proxy must extract client-origin IP from XFF"


def test_ffmpeg_service_defines_timeout_and_handles_expired():
    """OFF-05: Verify that FFmpegAssemblyService enforces timeouts and catches subprocess.TimeoutExpired."""
    svc = FFmpegAssemblyService()
    assert svc.timeout == DEFAULT_FFMPEG_TIMEOUT
    assert svc.timeout == 120.0

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["ffmpeg"], timeout=120.0)):
        with pytest.raises(RuntimeError) as exc_info:
            svc._run_ffmpeg(["ffmpeg", "-version"])
        assert "timed out after 120" in str(exc_info.value)


def test_production_secret_startup_assertion():
    """OFF-06: Verify that missing INTEGRATION_SERVICE_TOKEN in production raises RuntimeError."""
    with patch.dict(os.environ, {"APP_ENV": "production", "INTEGRATION_SERVICE_TOKEN": "", "EXPORT_SIGNING_SECRET": "secret"}):
        with pytest.raises(RuntimeError) as exc_info:
            Settings.from_env()
        assert "INTEGRATION_SERVICE_TOKEN is required when APP_ENV=production" in str(exc_info.value)


def test_inline_governance_check_sanitizes_unauthenticated_project_id():
    """OFF-07: Verify that unauthenticated inline-check strips project_id attribution."""
    res = client.post(
        "/api/governance/inline-check",
        json={"text": "A peaceful mountain view with clear sky", "project_id": "00000000-0000-0000-0000-000000000001"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "passed"


def test_public_download_export_manifest_with_capability_token():
    """OFF-08: Verify that signed download_token allows downloading manifest without integration token."""
    res = client.post("/api/projects", json={"topic": "Export Manifest Test", "duration_seconds": 10})
    p_id = res.json()["id"]
    owner_token = res.json()["owner_token"]

    # Create manifest
    manifest_res = client.post(
        f"/api/projects/{p_id}/exports/manifest",
        headers={"X-Project-Owner-Token": owner_token}
    )
    assert manifest_res.status_code == 200
    manifest_id = manifest_res.json()["manifest_id"]
    download_token = manifest_res.json()["download_token"]

    # 1. Download via capability token endpoint
    dl_res = client.get(f"/api/projects/{p_id}/exports/{manifest_id}/download?token={download_token}")
    assert dl_res.status_code == 200
    assert dl_res.json()["manifest_id"] == manifest_id
    assert "package_version" in dl_res.json()

    # 2. Invalid token rejected with 403
    bad_token_res = client.get(f"/api/projects/{p_id}/exports/{manifest_id}/download?token=invalid.token")
    assert bad_token_res.status_code == 403

    # 3. Mismatched project rejected with 404
    other_uuid = "00000000-0000-0000-0000-000000000002"
    mismatch_res = client.get(f"/api/projects/{other_uuid}/exports/{manifest_id}/download?token={download_token}")
    assert mismatch_res.status_code == 404
