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
