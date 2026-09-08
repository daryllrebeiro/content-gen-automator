import os
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from scripts.generate_video_e2e import generate_video_e2e, ApiClient, run_preflight_check  # noqa: E402
from app.api.routes import project_service  # noqa: E402
from uuid import UUID  # noqa: E402


def test_preflight_check_with_test_client():
    """Verify pre-flight check correctly identifies mock provider as live and handles key absence."""
    client = ApiClient(base_url="http://testserver", use_test_client=True)
    report = run_preflight_check(client, gemini_key=None)

    assert "providers" in report
    mock_p = next((p for p in report["providers"] if p["id"] == "mock"), None)
    assert mock_p is not None
    assert mock_p["is_available"] is True
    assert report["chosen_provider"] == "mock"
    assert report["quota_healthy"] is False


def test_end_to_end_generator_pipeline_mock(tmp_path):
    """
    Regression test for End-to-End Video Generator script.
    Asserts:
      1. 3 scenes generated
      2. 3 prompts approved
      3. 3 production jobs succeeded with valid artifact IDs
      4. One stitched output produced and downloaded
      5. Compliance certificate issuable and valid at the end
    """
    topic = "How Birds Build Nests"
    description = (
        "Start with a bird searching its surroundings for suitable materials—twigs, grass, "
        "leaves, fibers, and even mud. It carries each piece back and carefully positions, weaves, "
        "bends, and locks the materials together, gradually turning scattered scraps into a "
        "structured nest shaped specifically to protect its eggs and young."
    )
    output_file = str(tmp_path / "how-birds-build-nests.mp4")

    res = generate_video_e2e(
        topic=topic,
        description=description,
        gemini_key=None,
        video_provider="mock",
        base_url="http://testserver",
        output_path=output_file,
        use_test_client=True,
    )

    # 1. Pipeline execution success
    assert res["success"] is True
    project_id = res["project_id"]
    assert project_id is not None

    # 2. Assert 3 scenes generated, approved, and produced
    scenes = res["scenes"]
    assert len(scenes) == 3, f"Expected exactly 3 scenes, got {len(scenes)}"

    for s in scenes:
        assert s["scene_number"] in {1, 2, 3}
        assert s["prompt_snippet"], f"Scene {s['scene_number']} missing prompt text"
        assert s["job_id"], f"Scene {s['scene_number']} missing job_id"
        assert s["artifact_id"], f"Scene {s['scene_number']} missing artifact_id"
        assert s["video_type"] == "MOCK / SIMULATED"
        assert s["governance_decision"] == "passed"
        assert s["risk_score"] <= 0.15

    # 3. Assert Compliance Certificate issuable and cryptographically authentic
    assert res["certificate_id"].startswith("CERT-IBM-GOV-")
    assert res["certificate_valid"] is True

    # 4. Assert stitched vertical 30s video produced and downloaded locally
    assert os.path.exists(output_file)
    assert os.path.getsize(output_file) > 0
    with open(output_file, "rb") as f:
        data = f.read()
        assert len(data) > 0

    # 5. Verify repository state for platform exports
    project = project_service.repository.get(UUID(project_id))
    assert project is not None
    assert "YOUTUBE_SHORTS" in project.platform_exports
    yt_exp = project.platform_exports["YOUTUBE_SHORTS"]
    assert yt_exp.aspect_ratio == "9:16"
    assert yt_exp.export_status == "COMPLETED"
    assert yt_exp.publish_status == "PUBLISHED"
