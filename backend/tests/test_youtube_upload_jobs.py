"""Tests for YouTube upload jobs and publish endpoints."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_gate_check_and_publish_pipeline():
    # 1. Create project
    created = client.post(
        "/api/integrations/projects",
        json={"topic": "YouTube Publish test topic", "duration_seconds": 10},
        headers={"Idempotency-Key": "pub-create-01"},
    )
    assert created.status_code == 200
    project_id = created.json()["project_id"]

    # 2. Gate check initially should FAIL (missing prompt approval, production, review etc)
    gate_res = client.get(f"/api/integrations/projects/{project_id}/publish/gate")
    assert gate_res.status_code == 200
    assert gate_res.json()["can_publish"] is False
    assert len(gate_res.json()["failed_gates"]) > 0

    # 3. Generating prompt
    client.post(
        f"/api/integrations/projects/{project_id}/prompts/next",
        headers={"Idempotency-Key": "pub-prompt-01"},
    )
    # Approve prompt
    client.post(
        f"/api/integrations/projects/{project_id}/prompts/1/approve",
        json={"actor": "tester"},
        headers={"Idempotency-Key": "pub-approve-prompt-01"},
    )
    # Submit production
    prod = client.post(
        f"/api/integrations/projects/{project_id}/scenes/1/production",
        headers={"Idempotency-Key": "pub-submit-prod-01"},
    )
    job_id = prod.json()["job_id"]
    # Production callback success
    cb = client.post(
        f"/api/integrations/production-jobs/{job_id}/callback",
        json={
            "status": "SUCCEEDED",
            "duration_seconds": 10,
            "aspect_ratio": "9:16",
            "narration_end_seconds": 8.5,
            "checksum": "a" * 64,
            "artifact_url": "https://storage.example/clip.mp4",
        },
    )
    assert cb.status_code == 200
    artifact_id = cb.json()["artifact_id"]
    
    # Clip review approval
    client.post(
        f"/api/integrations/projects/{project_id}/clips/1/review",
        json={
            "artifact_id": artifact_id,
            "decision": "approved",
            "actor": "tester",
        },
    )
    # Generate manifest
    export_res = client.post(f"/api/projects/{project_id}/exports/manifest")
    assert export_res.status_code == 200
    manifest_id = export_res.json()["manifest_id"]

    # Approve final review
    client.post(
        f"/api/integrations/projects/{project_id}/final-review/approve",
        json={"actor": "reviewer-1", "manifest_id": manifest_id},
    )

    # 4. Now gate check should PASS!
    gate_res = client.get(f"/api/integrations/projects/{project_id}/publish/gate")
    assert gate_res.status_code == 200
    assert gate_res.json()["can_publish"] is True

    # 5. Publish the project
    pub_res = client.post(
        f"/api/integrations/projects/{project_id}/publish",
        json={"actor": "tester", "idempotency_key": "pub-idemp-01"},
    )
    assert pub_res.status_code == 200
    upload_job_id = pub_res.json()["job_id"]
    assert pub_res.json()["status"] == "QUEUED"

    # Verify project status advanced to PUBLISHING_PENDING
    proj_res = client.get(f"/api/projects/{project_id}")
    assert proj_res.json()["status"] == "PUBLISHING_PENDING"

    # Test publish idempotency
    pub_replay = client.post(
        f"/api/integrations/projects/{project_id}/publish",
        json={"actor": "tester", "idempotency_key": "pub-idemp-01"},
    )
    assert pub_replay.status_code == 200
    assert pub_replay.json()["job_id"] == upload_job_id

    # 6. YouTube callback published
    cb_res = client.post(
        f"/api/integrations/youtube-upload-jobs/{upload_job_id}/callback",
        json={
            "status": "PUBLISHED",
            "youtube_video_id": "yt-video-123",
            "youtube_url": "https://youtube.com/watch?v=video123",
        },
    )
    assert cb_res.status_code == 200
    assert cb_res.json()["status"] == "PUBLISHED"

    # Verify project status advanced to PUBLISHED
    proj_res2 = client.get(f"/api/projects/{project_id}")
    assert proj_res2.json()["status"] == "PUBLISHED"


def test_publish_failure_callback():
    # Setup a new project and publish it
    created = client.post(
        "/api/integrations/projects",
        json={"topic": "YouTube Publish fail topic", "duration_seconds": 10},
        headers={"Idempotency-Key": "pub-fail-create"},
    )
    project_id = created.json()["project_id"]

    client.post(f"/api/integrations/projects/{project_id}/prompts/next", headers={"Idempotency-Key": "pub-fail-prompt"})
    client.post(f"/api/integrations/projects/{project_id}/prompts/1/approve", json={"actor": "tester"}, headers={"Idempotency-Key": "pub-fail-app-prompt"})
    prod = client.post(f"/api/integrations/projects/{project_id}/scenes/1/production", headers={"Idempotency-Key": "pub-fail-prod"})
    prod_job = prod.json()
    cb = client.post(
        f"/api/integrations/production-jobs/{prod_job['job_id']}/callback",
        json={"status": "SUCCEEDED", "duration_seconds": 10, "aspect_ratio": "9:16", "narration_end_seconds": 8.5, "checksum": "abc", "artifact_url": "url"},
    )
    assert cb.status_code == 200
    artifact_id = cb.json()["artifact_id"]
    client.post(f"/api/integrations/projects/{project_id}/clips/1/review", json={"artifact_id": artifact_id, "decision": "approved", "actor": "tester"})
    exp = client.post(f"/api/projects/{project_id}/exports/manifest")
    assert exp.status_code == 200
    client.post(f"/api/integrations/projects/{project_id}/final-review/approve", json={"actor": "tester", "manifest_id": exp.json()["manifest_id"]})

    pub = client.post(f"/api/integrations/projects/{project_id}/publish", json={"actor": "tester", "idempotency_key": "pub-fail-key"})
    job_id = pub.json()["job_id"]

    # Callback failed
    cb = client.post(
        f"/api/integrations/youtube-upload-jobs/{job_id}/callback",
        json={
            "status": "FAILED_PERMANENT",
            "error": "Video upload quota exceeded.",
            "error_class": "YouTubeQuotaExceeded",
        },
    )
    assert cb.status_code == 200
    assert cb.json()["status"] == "FAILED_PERMANENT"

    # Verify project status advanced to PUBLISH_FAILED
    proj = client.get(f"/api/projects/{project_id}")
    assert proj.json()["status"] == "PUBLISH_FAILED"
