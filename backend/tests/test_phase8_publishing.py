import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_phase8_youtube_metadata_validation_endpoint():
    """Phase 8: Validate metadata against YouTube Shorts technical specifications."""
    # 1. Valid metadata
    valid_res = client.post(
        "/api/integrations/publish/metadata/check",
        json={
            "title": "Ancient Civilizations: The Bronze Age Collapse #Shorts",
            "description": "How the ancient Mediterranean collapsed in 1177 BC. #Shorts #History",
            "tags": ["Shorts", "History", "AncientHistory", "Documentary"],
        },
    )
    assert valid_res.status_code == 200
    assert valid_res.json()["valid"] is True
    assert len(valid_res.json()["errors"]) == 0

    # 2. Oversized title (>100 chars)
    invalid_title_res = client.post(
        "/api/integrations/publish/metadata/check",
        json={
            "title": "A" * 105,
            "description": "Test description",
        },
    )
    assert invalid_title_res.status_code == 200
    assert invalid_title_res.json()["valid"] is False
    assert any("exceeds maximum permitted length" in err for err in invalid_title_res.json()["errors"])

    # 3. Control character in title
    ctrl_char_res = client.post(
        "/api/integrations/publish/metadata/check",
        json={
            "title": "Bad\x00Title #Shorts",
            "description": "Test description",
        },
    )
    assert ctrl_char_res.status_code == 200
    assert ctrl_char_res.json()["valid"] is False
    assert any("control characters" in err for err in ctrl_char_res.json()["errors"])

    # 4. Missing / non-existent thumbnail file
    bad_thumb_res = client.post(
        "/api/integrations/publish/metadata/check",
        json={
            "title": "Thumbnail Test #Shorts",
            "description": "Test description",
            "thumbnail_path": "non_existent_thumbnail_file_12345.png",
        },
    )
    assert bad_thumb_res.status_code == 200
    assert bad_thumb_res.json()["valid"] is False
    assert any("does not exist" in err for err in bad_thumb_res.json()["errors"])


def test_phase8_unpublish_and_rollback_workflow():
    """Phase 8: Operational unpublish / rollback transitions project to UNPUBLISHED."""
    # 1. Setup a project through to PUBLISHED
    created = client.post(
        "/api/integrations/projects",
        json={"topic": "Phase 8 Rollback Topic", "duration_seconds": 10},
        headers={"Idempotency-Key": f"p8-create-{uuid.uuid4()}"},
    )
    assert created.status_code == 200
    p_id = created.json()["project_id"]

    # Attempting to unpublish a fresh, non-published project should fail with 400
    early_unpub = client.post(
        f"/api/integrations/projects/{p_id}/publish/unpublish",
        json={"actor": "emergency_officer", "reason": "Test early abort"},
    )
    assert early_unpub.status_code == 400

    # Advance project through prompts, production, and reviews
    client.post(f"/api/integrations/projects/{p_id}/prompts/next", headers={"Idempotency-Key": f"p8-pr-{uuid.uuid4()}"})
    client.post(f"/api/integrations/projects/{p_id}/prompts/1/approve", json={"actor": "tester"}, headers={"Idempotency-Key": f"p8-ap-{uuid.uuid4()}"})
    prod = client.post(f"/api/integrations/projects/{p_id}/scenes/1/production", headers={"Idempotency-Key": f"p8-prod-{uuid.uuid4()}"})
    job_id = prod.json()["job_id"]

    cb = client.post(
        f"/api/integrations/production-jobs/{job_id}/callback",
        json={"status": "SUCCEEDED", "duration_seconds": 10, "aspect_ratio": "9:16", "narration_end_seconds": 8.5, "checksum": "a" * 64, "artifact_url": "https://storage.example/clip.mp4"},
    )
    artifact_id = cb.json()["artifact_id"]
    client.post(f"/api/integrations/projects/{p_id}/clips/1/review", json={"artifact_id": artifact_id, "decision": "approved", "actor": "tester"})

    exp = client.post(f"/api/projects/{p_id}/exports/manifest")
    manifest_id = exp.json()["manifest_id"]
    client.post(f"/api/integrations/projects/{p_id}/final-review/approve", json={"actor": "tester", "manifest_id": manifest_id})

    # Publish
    pub = client.post(f"/api/integrations/projects/{p_id}/publish", json={"actor": "tester", "idempotency_key": f"p8-pub-{uuid.uuid4()}"})
    assert pub.status_code == 200
    upload_job_id = pub.json()["job_id"]

    # Mark as published via YouTube callback
    client.post(
        f"/api/integrations/youtube-upload-jobs/{upload_job_id}/callback",
        json={"status": "PUBLISHED", "youtube_video_id": "yt_rollback_vid_01", "youtube_url": "https://youtu.be/yt_rollback_vid_01"},
    )

    # Verify project is PUBLISHED
    proj = client.get(f"/api/projects/{p_id}")
    assert proj.json()["status"] == "PUBLISHED"

    # Now execute UNPUBLISH / ROLLBACK
    unpub_res = client.post(
        f"/api/integrations/projects/{p_id}/publish/unpublish",
        json={"actor": "head_of_compliance", "reason": "Retracted for fact re-grounding"},
    )
    assert unpub_res.status_code == 200
    assert unpub_res.json()["status"] == "UNPUBLISHED"
    assert "successfully rolled back" in unpub_res.json()["message"]

    # Verify project status in DB is now UNPUBLISHED
    proj_after = client.get(f"/api/projects/{p_id}")
    assert proj_after.json()["status"] == "UNPUBLISHED"
