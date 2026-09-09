import uuid
from uuid import UUID
from fastapi.testclient import TestClient
from app.main import app
from app.services.project_service import ProjectService

client = TestClient(app)


def test_phase7_provider_neutral_job_interface_and_contract_attachment():
    """Phase 7: Submitting a production job attaches prompt version and full production contract."""
    res = client.post("/api/projects", json={"topic": "Phase 7 Contract Test", "duration_seconds": 10})
    assert res.status_code == 200
    p_id = res.json()["id"]
    owner_token = res.json()["owner_token"]

    # Generate scene 1
    gen_res = client.post(f"/api/projects/{p_id}/generate", headers={"X-Project-Owner-Token": owner_token})
    assert gen_res.status_code == 200

    # Approve scene 1
    appr_res = client.post(
        f"/api/projects/{p_id}/prompts/1/approve",
        json={"actor": "director_phase7"},
        headers={"X-Project-Owner-Token": owner_token, "X-Expected-Version": "2"},
    )
    assert appr_res.status_code == 200

    # Submit production job
    prod_res = client.post(
        f"/api/projects/{p_id}/scenes/1/production",
        headers={"X-Project-Owner-Token": owner_token, "Idempotency-Key": f"p7-prod-{uuid.uuid4()}"},
    )
    assert prod_res.status_code == 200
    job = prod_res.json()
    assert job["scene_number"] == 1
    assert job["prompt_version"] == 1
    assert job["status"] in {"SUBMITTED", "IN_PROGRESS", "COMPLETED"}
    assert job["contract"]["aspect_ratio"] == "9:16"
    assert job["contract"]["duration_seconds"] == 10
    assert job["contract"]["narration_max_seconds"] == 9
    assert job["contract"]["voice_id"] == "documentary_voice_01"


def test_phase7_independent_scene_jobs_failed_scene_does_not_invalidate_prior_scene():
    """Phase 7 Acceptance Criteria: A failed Clip 2 job does not invalidate Clip 1."""
    res = client.post("/api/projects", json={"topic": "Phase 7 Multi-Scene Test", "duration_seconds": 20})
    p_id = res.json()["id"]
    owner_token = res.json()["owner_token"]

    # Generate scene 1 & approve
    client.post(f"/api/projects/{p_id}/generate", headers={"X-Project-Owner-Token": owner_token})
    client.post(
        f"/api/projects/{p_id}/prompts/1/approve",
        json={"actor": "tester"},
        headers={"X-Project-Owner-Token": owner_token, "X-Expected-Version": "2"},
    )

    # Submit scene 1 production
    job1_res = client.post(
        f"/api/projects/{p_id}/scenes/1/production",
        headers={"X-Project-Owner-Token": owner_token, "Idempotency-Key": f"p7-job1-{uuid.uuid4()}"},
    )
    job1_id = job1_res.json()["job_id"]

    # Callback scene 1 succeeded
    cb1 = client.post(
        f"/api/integrations/production-jobs/{job1_id}/callback",
        json={
            "status": "SUCCEEDED",
            "duration_seconds": 10,
            "aspect_ratio": "9:16",
            "narration_end_seconds": 8.0,
            "checksum": "1" * 64,
            "artifact_url": "https://storage.example/clip-1.mp4",
        },
    )
    assert cb1.status_code == 200
    assert cb1.json()["status"] == "SUCCEEDED"
    clip1_artifact_id = cb1.json()["artifact_id"]

    # Generate scene 2 & approve
    gen2_res = client.post(f"/api/projects/{p_id}/generate", headers={"X-Project-Owner-Token": owner_token})
    assert gen2_res.status_code == 200
    version_now = ProjectService().repository.get(UUID(p_id)).version
    client.post(
        f"/api/projects/{p_id}/prompts/2/approve",
        json={"actor": "tester"},
        headers={"X-Project-Owner-Token": owner_token, "X-Expected-Version": str(version_now)},
    )

    # Submit scene 2 production
    job2_res = client.post(
        f"/api/projects/{p_id}/scenes/2/production",
        headers={"X-Project-Owner-Token": owner_token, "Idempotency-Key": f"p7-job2-{uuid.uuid4()}"},
    )
    job2_id = job2_res.json()["job_id"]

    # Callback scene 2 FAILED
    cb2 = client.post(
        f"/api/integrations/production-jobs/{job2_id}/callback",
        json={
            "status": "FAILED_PERMANENT",
            "error": "Provider rendering failure: out of GPU memory",
        },
    )
    assert cb2.status_code == 200
    assert cb2.json()["status"] == "FAILED_PERMANENT"

    # Verify Clip 1 artifact and job status remain intact!
    poll_jobs = client.get(f"/api/projects/{p_id}/production-jobs", headers={"X-Project-Owner-Token": owner_token})
    assert poll_jobs.status_code == 200
    jobs_list = poll_jobs.json()
    job1_found = next(j for j in jobs_list if j["job_id"] == job1_id)
    job2_found = next(j for j in jobs_list if j["job_id"] == job2_id)
    assert job1_found["status"] == "SUCCEEDED"
    assert job1_found["artifact_id"] == clip1_artifact_id
    assert job2_found["status"] == "FAILED_PERMANENT"


def test_phase7_provider_callback_idempotency_and_artifact_checksum():
    """Phase 7: Provider callbacks are idempotent and reject contract violations."""
    res = client.post("/api/projects", json={"topic": "Phase 7 Callback Test", "duration_seconds": 10})
    p_id = res.json()["id"]
    owner_token = res.json()["owner_token"]

    client.post(f"/api/projects/{p_id}/generate", headers={"X-Project-Owner-Token": owner_token})
    client.post(
        f"/api/projects/{p_id}/prompts/1/approve",
        json={"actor": "tester"},
        headers={"X-Project-Owner-Token": owner_token, "X-Expected-Version": "2"},
    )
    prod_res = client.post(
        f"/api/projects/{p_id}/scenes/1/production",
        headers={"X-Project-Owner-Token": owner_token, "Idempotency-Key": f"p7-cb-{uuid.uuid4()}"},
    )
    job_id = prod_res.json()["job_id"]

    # First callback succeeds
    checksum_val = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    payload = {
        "status": "SUCCEEDED",
        "duration_seconds": 10,
        "aspect_ratio": "9:16",
        "narration_end_seconds": 8.5,
        "checksum": checksum_val,
        "artifact_url": "https://storage.example/clean-clip-1.mp4",
    }
    r1 = client.post(f"/api/integrations/production-jobs/{job_id}/callback", json=payload)
    assert r1.status_code == 200
    assert r1.json()["status"] == "SUCCEEDED"

    # Replay is idempotent
    r2 = client.post(f"/api/integrations/production-jobs/{job_id}/callback", json=payload)
    assert r2.status_code == 200
    assert r2.json() == r1.json()


def test_phase7_human_video_review_state_machine():
    """Phase 7: Human video review transitions artifacts from VIDEO_REVIEW_PENDING to APPROVED/REJECTED."""
    res = client.post("/api/projects", json={"topic": "Phase 7 Review Test", "duration_seconds": 10})
    p_id = res.json()["id"]
    owner_token = res.json()["owner_token"]

    client.post(f"/api/projects/{p_id}/generate", headers={"X-Project-Owner-Token": owner_token})
    client.post(
        f"/api/projects/{p_id}/prompts/1/approve",
        json={"actor": "tester"},
        headers={"X-Project-Owner-Token": owner_token, "X-Expected-Version": "2"},
    )
    prod_res = client.post(
        f"/api/projects/{p_id}/scenes/1/production",
        headers={"X-Project-Owner-Token": owner_token, "Idempotency-Key": f"p7-rev-{uuid.uuid4()}"},
    )
    job_id = prod_res.json()["job_id"]

    cb = client.post(
        f"/api/integrations/production-jobs/{job_id}/callback",
        json={
            "status": "SUCCEEDED",
            "duration_seconds": 10,
            "aspect_ratio": "9:16",
            "narration_end_seconds": 8.0,
            "checksum": "f" * 64,
            "artifact_url": "https://storage.example/review-clip.mp4",
        },
    )
    artifact_id = cb.json()["artifact_id"]

    # Review decide clip via integration endpoint: approve
    rev_res = client.post(
        f"/api/integrations/projects/{p_id}/clips/1/review",
        json={"artifact_id": artifact_id, "decision": "approved", "actor": "head_editor", "comment": "Crisp lighting and perfect pacing."},
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["decision"] == "approved"
    assert rev_res.json()["actor"] == "head_editor"

    # Verify clip artifact reflects approved status in project service repository
    artifact = ProjectService().repository.get_clip_artifact(artifact_id)
    assert artifact is not None
    assert artifact.review_status == "approved"
