import os
import json
from uuid import uuid4, UUID
from app.domain.project import Project, ProjectInput, Platform
from app.services.publish_adapters import (
    get_publish_adapter,
    YouTubePublishAdapter,
    TikTokPublishAdapter,
    InstagramPublishAdapter
)

def test_get_publish_adapter_factory():
    yt = get_publish_adapter(Platform.YOUTUBE_SHORTS)
    assert isinstance(yt, YouTubePublishAdapter)

    tt = get_publish_adapter(Platform.TIKTOK)
    assert isinstance(tt, TikTokPublishAdapter)

    ig = get_publish_adapter(Platform.INSTAGRAM_REELS)
    assert isinstance(ig, InstagramPublishAdapter)

def test_youtube_publish_adapter():
    inp = ProjectInput(topic="Bioluminescence")
    proj = Project(id=uuid4(), input=inp)
    adapter = YouTubePublishAdapter()
    res = adapter.publish(proj, "app/static/output/dummy.mp4")
    assert res.platform == Platform.YOUTUBE_SHORTS
    assert res.status == "PUBLISHED"
    assert "youtube.com/shorts" in res.published_url

def test_tiktok_publish_adapter_manual_packaging(monkeypatch):
    monkeypatch.delenv("TIKTOK_ACCESS_TOKEN", raising=False)
    inp = ProjectInput(topic="Underwater Geysers")
    proj = Project(id=uuid4(), input=inp)
    proj.story_hook = "Did you know boiling water erupts miles beneath the Pacific?"

    adapter = TikTokPublishAdapter()
    res = adapter.publish(proj, "app/static/output/dummy_tiktok.mp4")

    assert res.platform == Platform.TIKTOK
    assert res.status == "READY_FOR_MANUAL_UPLOAD"
    assert res.package_dir is not None
    assert os.path.exists(f"{res.package_dir}/captions.vtt")
    assert os.path.exists(f"{res.package_dir}/post_copy.txt")
    assert os.path.exists(f"{res.package_dir}/manifest.json")

    with open(f"{res.package_dir}/manifest.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["platform"] == "TIKTOK"
        assert "#TikTokShorts" in data["hashtags"]

def test_instagram_publish_adapter_manual_packaging(monkeypatch):
    monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)
    inp = ProjectInput(topic="Supermassive Black Holes")
    proj = Project(id=uuid4(), input=inp)
    proj.story_hook = "Nothing escapes their gravitational pull."

    adapter = InstagramPublishAdapter()
    res = adapter.publish(proj, "app/static/output/dummy_reels.mp4")

    assert res.platform == Platform.INSTAGRAM_REELS
    assert res.status == "READY_FOR_MANUAL_UPLOAD"
    assert res.package_dir is not None
    assert os.path.exists(f"{res.package_dir}/captions.vtt")
    assert os.path.exists(f"{res.package_dir}/post_copy.txt")
    assert os.path.exists(f"{res.package_dir}/manifest.json")

    with open(f"{res.package_dir}/manifest.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["platform"] == "INSTAGRAM_REELS"
        assert "#Reels" in data["hashtags"]

def test_packaging_syntax_and_manifest_hygiene(monkeypatch):
    """Verify generated captions.vtt has valid WebVTT syntax and manifest.json leaks no server paths or secrets."""
    monkeypatch.delenv("TIKTOK_ACCESS_TOKEN", raising=False)
    inp = ProjectInput(topic="Deep Sea Vent Exploration")
    proj = Project(id=uuid4(), input=inp)
    proj.story_hook = "Life thrives in superheated volcanic chimneys."
    
    adapter = TikTokPublishAdapter()
    res = adapter.publish(proj, "app/static/output/dummy_tiktok.mp4")
    
    # 1. Validate WebVTT syntax
    vtt_path = f"{res.package_dir}/captions.vtt"
    with open(vtt_path, "r", encoding="utf-8") as f:
        vtt_content = f.read()
        assert vtt_content.startswith("WEBVTT\n\n")
        assert "-->" in vtt_content
        assert "Life thrives in superheated volcanic chimneys." in vtt_content

    # 2. Validate manifest.json hygiene (no internal server paths, no API keys, valid JSON)
    manifest_path = f"{res.package_dir}/manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        assert manifest["platform"] == "TIKTOK"
        assert "Deep Sea Vent Exploration" in manifest["caption"] or "Life thrives" in manifest["caption"]
        assert manifest["video_file"].startswith("tiktok_") and manifest["video_file"].endswith(".mp4")
        # Confirm absolute filesystem path is NOT leaked in video_file
        assert "/" not in manifest["video_file"]
        assert "\\" not in manifest["video_file"]
        # Confirm no internal keys leaked
        assert "api_key" not in manifest
        assert "secret" not in manifest
        assert "token" not in manifest


def test_platform_export_download_security_hardening(monkeypatch):
    """Adversarial security audit of export download route: path traversal, file whitelisting, and auth."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import settings
    from app.api.routes import project_service

    client = TestClient(app)

    # 1. Create a project
    create_resp = client.post("/api/projects", json={"topic": "Bioluminescent Squid"})
    assert create_resp.status_code == 200
    proj_id = create_resp.json()["id"]

    # 2. Package TikTok manual export for this project
    proj = project_service.repository.get(UUID(proj_id))
    adapter = TikTokPublishAdapter()
    res = adapter.publish(proj, "app/static/output/dummy_export.mp4")

    # 3. Valid download succeeds
    dl_resp = client.get(f"/api/projects/{proj_id}/platform-exports/tiktok/download/manifest.json")
    assert dl_resp.status_code == 200
    assert dl_resp.json()["platform"] == "TIKTOK"

    # 4. Path traversal attempt 1: filename containing '..'
    trav_resp1 = client.get(f"/api/projects/{proj_id}/platform-exports/tiktok/download/..secret.key")
    assert trav_resp1.status_code == 400
    assert "Path traversal" in trav_resp1.json()["detail"]

    # 5. Path traversal attempt 2: URL-encoded traversal chars (% or slashes)
    trav_resp2 = client.get(f"/api/projects/{proj_id}/platform-exports/tiktok/download/manifest%20secret.json")
    assert trav_resp2.status_code == 400
    assert "Path traversal" in trav_resp2.json()["detail"]

    # 6. Forbidden non-whitelisted file attempt
    forbid_resp = client.get(f"/api/projects/{proj_id}/platform-exports/tiktok/download/secret_config.json")
    assert forbid_resp.status_code == 400
    assert "Forbidden" in forbid_resp.json()["detail"]

    # 7. Non-existent project
    non_existent_id = uuid4()
    not_found_resp = client.get(f"/api/projects/{non_existent_id}/platform-exports/tiktok/download/manifest.json")
    assert not_found_resp.status_code == 404

    # 8. Access control test in production mode
    from app.config import Settings
    prod_settings = Settings(
        app_env="production",
        log_level=settings.log_level,
        database_url=settings.database_url,
        project_repository=settings.project_repository,
        llm_provider=settings.llm_provider,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        cors_origins=settings.cors_origins,
        integration_service_token="director-secret-12345",
        export_signing_secret=settings.export_signing_secret,
    )
    monkeypatch.setattr("app.api.routes.settings", prod_settings)

    # Unauthorized request in production
    unauth_resp = client.get(f"/api/projects/{proj_id}/platform-exports/tiktok/download/manifest.json")
    assert unauth_resp.status_code == 403
    assert "Access denied" in unauth_resp.json()["detail"]

    # Authorized request with Bearer token
    auth_resp = client.get(
        f"/api/projects/{proj_id}/platform-exports/tiktok/download/manifest.json",
        headers={"Authorization": "Bearer director-secret-12345"}
    )
    assert auth_resp.status_code == 200

