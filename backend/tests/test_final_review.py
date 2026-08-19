"""Tests for final review API endpoints."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_final_review_submission_approval_and_rejection():
    # 1. Create project
    created = client.post(
        "/api/integrations/projects",
        json={"topic": "Final review test topic", "duration_seconds": 10},
        headers={"Idempotency-Key": "fr-create-01"},
    )
    assert created.status_code == 200
    project_id = created.json()["project_id"]

    # 2. Get prompt
    prompt_res = client.post(
        f"/api/integrations/projects/{project_id}/prompts/next",
        headers={"Idempotency-Key": "fr-prompt-01"},
    )
    assert prompt_res.status_code == 200

    # 3. Approve prompt
    app_res = client.post(
        f"/api/integrations/projects/{project_id}/prompts/1/approve",
        json={"actor": "tester", "comment": "Approved prompt"},
        headers={"Idempotency-Key": "fr-approve-prompt-01"},
    )
    assert app_res.status_code == 200

    # 4. Submit production
    prod_res = client.post(
        f"/api/integrations/projects/{project_id}/scenes/1/production",
        headers={"Idempotency-Key": "fr-submit-prod-01"},
    )
    assert prod_res.status_code == 200
    job_id = prod_res.json()["job_id"]

    # 5. Production callback success
    cb_res = client.post(
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
    assert cb_res.status_code == 200
    artifact_id = cb_res.json()["artifact_id"]

    # 6. Clip review approval
    clip_rev = client.post(
        f"/api/integrations/projects/{project_id}/clips/1/review",
        json={
            "artifact_id": artifact_id,
            "decision": "approved",
            "actor": "tester",
            "comment": "Good clip",
        },
    )
    assert clip_rev.status_code == 200

    # 7. Create the manifest
    export_res = client.post(f"/api/projects/{project_id}/exports/manifest")
    assert export_res.status_code == 200
    manifest_id = export_res.json()["manifest_id"]


    # 8. Check final review status initially
    status_res = client.get(f"/api/integrations/projects/{project_id}/final-review")
    assert status_res.status_code == 200
    assert status_res.json()["has_review"] is False

    # 9. Approve final review
    approve_res = client.post(
        f"/api/integrations/projects/{project_id}/final-review/approve",
        json={"actor": "reviewer-1", "manifest_id": manifest_id, "comment": "Excellent metadata package"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["decision"] == "approved"
    assert approve_res.json()["project_status"] == "VIDEO_APPROVED"

    # Check status again
    status_res = client.get(f"/api/integrations/projects/{project_id}/final-review")
    assert status_res.status_code == 200
    assert status_res.json()["has_review"] is True
    assert status_res.json()["decision"] == "approved"

    # 10. Reject final review (for testing state updates)
    reject_res = client.post(
        f"/api/integrations/projects/{project_id}/final-review/reject",
        json={"actor": "reviewer-1", "manifest_id": manifest_id, "comment": "Incorrect tags"},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["decision"] == "rejected"
    assert reject_res.json()["project_status"] == "VIDEO_REJECTED"


def test_final_review_errors():
    # Attempt to review non-existent project
    resp = client.post(
        "/api/integrations/projects/00000000-0000-0000-0000-000000000000/final-review/approve",
        json={"actor": "reviewer-1", "manifest_id": "abc"},
    )
    assert resp.status_code == 404

    # Get review for non-existent project
    resp = client.get("/api/integrations/projects/00000000-0000-0000-0000-000000000000/final-review")
    assert resp.status_code == 404
