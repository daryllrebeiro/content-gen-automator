import os
from uuid import uuid4
import pytest
from app.domain.project import Project, ProjectInput, Platform, PlatformExport
from app.services.ffmpeg_service import FFmpegAssemblyService
from app.services.publishing_gate_service import PublishingGateService

def test_project_input_multi_platform_defaults():
    inp = ProjectInput(topic="Quantum Mechanics")
    assert inp.target_platforms == [Platform.YOUTUBE_SHORTS]
    assert inp.model_tier == "flagship"

def test_project_multi_platform_custom_selection():
    inp = ProjectInput(
        topic="Ancient Civilizations",
        target_platforms=[Platform.YOUTUBE_SHORTS, Platform.TIKTOK, Platform.INSTAGRAM_REELS],
        model_tier="fast_draft"
    )
    assert len(inp.target_platforms) == 3
    assert Platform.TIKTOK in inp.target_platforms
    assert inp.model_tier == "fast_draft"

def test_ffmpeg_export_platform_targets_fanout(tmp_path):
    project_id = str(uuid4())
    inp = ProjectInput(
        topic="Deep Sea Wonders",
        target_platforms=[Platform.YOUTUBE_SHORTS, Platform.TIKTOK, Platform.INSTAGRAM_REELS]
    )
    proj = Project(id=uuid4(), input=inp)
    
    ffmpeg_svc = FFmpegAssemblyService()
    exports = ffmpeg_svc.export_platform_targets(proj, dry_run=True)

    assert len(exports) == 3
    assert "YOUTUBE_SHORTS" in exports
    assert "TIKTOK" in exports
    assert "INSTAGRAM_REELS" in exports

    yt_exp = exports["YOUTUBE_SHORTS"]
    assert yt_exp.aspect_ratio == "9:16"
    assert yt_exp.export_status == "COMPLETED"
    assert os.path.exists(yt_exp.output_asset_ref)
    with open(yt_exp.output_asset_ref, "r", encoding="utf-8") as f:
        content = f.read()
        assert "EXPORT_YOUTUBE_9_16" in content

    tiktok_exp = exports["TIKTOK"]
    assert tiktok_exp.aspect_ratio == "9:16"
    assert tiktok_exp.export_status == "COMPLETED"
    assert os.path.exists(tiktok_exp.output_asset_ref)
    with open(tiktok_exp.output_asset_ref, "r", encoding="utf-8") as f:
        content = f.read()
        assert "HIGH_ENERGY" in content

    reels_exp = exports["INSTAGRAM_REELS"]
    assert reels_exp.aspect_ratio == "9:16"
    assert reels_exp.export_status == "COMPLETED"
    assert os.path.exists(reels_exp.output_asset_ref)
    with open(reels_exp.output_asset_ref, "r", encoding="utf-8") as f:
        content = f.read()
        assert "AESTHETIC" in content

def test_publishing_gate_validates_platform_exports():
    gate_svc = PublishingGateService()
    inp = ProjectInput(
        topic="Solar Storms",
        target_platforms=[Platform.YOUTUBE_SHORTS, Platform.TIKTOK]
    )
    proj = Project(id=uuid4(), input=inp)

    # Incomplete exports
    proj.platform_exports["YOUTUBE_SHORTS"] = PlatformExport(
        platform=Platform.YOUTUBE_SHORTS,
        aspect_ratio="9:16",
        output_asset_ref="path.mp4",
        export_status="FAILED"
    )
    report = gate_svc.check(proj, repository=type("Repo", (), {"approval_events": []})())
    assert not report.can_publish
    assert any("Platform target 'YOUTUBE_SHORTS' is missing completed media export." in f for f in report.failed_gates)


def test_gate_8_blocks_publish_with_two_of_three_exports_complete():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.domain.project import ProjectStatus
    from app.api.routes import project_service
    from app.domain.integration import FinalReviewEvent

    client = TestClient(app)

    # Create project with 3 platforms
    inp = ProjectInput(
        topic="Planetary Rings",
        target_platforms=[Platform.YOUTUBE_SHORTS, Platform.TIKTOK, Platform.INSTAGRAM_REELS],
        duration_seconds=10
    )
    proj = project_service.create(inp)
    proj.status = ProjectStatus.VIDEO_APPROVED

    # Provide complete exports for ONLY 2 of 3 platforms (YouTube and TikTok, missing Instagram Reels)
    proj.platform_exports["YOUTUBE_SHORTS"] = PlatformExport(
        platform=Platform.YOUTUBE_SHORTS,
        aspect_ratio="9:16",
        output_asset_ref="app/static/output/rings_youtube_9_16.mp4",
        export_status="COMPLETED"
    )
    proj.platform_exports["TIKTOK"] = PlatformExport(
        platform=Platform.TIKTOK,
        aspect_ratio="9:16",
        output_asset_ref="app/static/output/rings_tiktok_9_16.mp4",
        export_status="COMPLETED"
    )
    project_service.repository.save(proj)

    # Fake final review event so earlier gates don't fail before Gate 8
    if hasattr(project_service.repository, "final_reviews"):
        project_service.repository.final_reviews[str(proj.id)] = FinalReviewEvent(
            project_id=str(proj.id),
            manifest_id="manifest-test",
            decision="APPROVED",
            actor="director",
            comment="Approved"
        )

    # Call integration publish endpoint
    response = client.post(
        f"/api/integrations/projects/{proj.id}/publish",
        json={"actor": "director", "idempotency_key": f"test-gate-8-{uuid4()}"},
        headers={"X-API-Key": "local-dev-key"}
    )

    # Verify publish is actually blocked with HTTP 422
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    failed_gates = data["detail"].get("failed_gates", [])
    assert any("Platform target 'INSTAGRAM_REELS' is missing completed media export." in g for g in failed_gates)


def test_cost_ceiling_enforcement_multi_platform_flagship_project():
    """Verify cost ceiling (HTTP 429) triggers when multi-platform flagship reasoning consumes budget."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 1. Create multi-platform project with flagship model tier and a tight token budget (100 tokens)
    create_res = client.post(
        "/api/projects",
        json={
            "topic": "Quantum Teleportation Across Continents",
            "duration_seconds": 10,
            "target_platforms": ["YOUTUBE_SHORTS", "TIKTOK", "INSTAGRAM_REELS"],
            "model_tier": "flagship",
            "video_provider": "runway",
            "token_budget": 100,
        }
    )
    assert create_res.status_code == 200
    p_id = create_res.json()["id"]

    # 2. Generate prompt (consumes ~400+ tokens)
    gen_res = client.post(f"/api/projects/{p_id}/generate")
    assert gen_res.status_code == 200

    # 3. Approve prompt
    appr_res = client.post(f"/api/projects/{p_id}/prompts/1/approve", json={"decision": "APPROVE", "actor": "director"})
    assert appr_res.status_code == 200

    # 4. Attempting to submit production job must trigger HTTP 429 Cost Ceiling Exceeded
    prod_res = client.post(f"/api/projects/{p_id}/scenes/1/production")
    assert prod_res.status_code == 429
    assert "Cost ceiling exceeded" in prod_res.json()["detail"]
    assert "tokens" in prod_res.json()["detail"]


