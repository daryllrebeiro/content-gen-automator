from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_production_job_is_bound_to_prompt_version_and_callback_is_idempotent():
    created = client.post("/api/integrations/projects", json={"topic": "A clip must obey its production contract", "duration_seconds": 10}, headers={"Idempotency-Key": "production-create-001"})
    project_id = created.json()["project_id"]
    client.post(f"/api/integrations/projects/{project_id}/prompts/next", headers={"Idempotency-Key": "production-prompt-001"})
    blocked = client.post(f"/api/integrations/projects/{project_id}/scenes/1/production", headers={"Idempotency-Key": "production-job-001"})
    client.post(f"/api/integrations/projects/{project_id}/prompts/1/approve", json={"actor": "producer", "comment": "Approved."}, headers={"Idempotency-Key": "production-approval-001"})
    submitted = client.post(f"/api/integrations/projects/{project_id}/scenes/1/production", headers={"Idempotency-Key": "production-job-001"})
    job_id = submitted.json()["job_id"]
    payload = {"status": "SUCCEEDED", "duration_seconds": 10, "aspect_ratio": "9:16", "narration_end_seconds": 8.5, "checksum": "a" * 64, "artifact_url": "https://storage.example/clip-1.mp4"}
    callback = client.post(f"/api/integrations/production-jobs/{job_id}/callback", json=payload)
    replay = client.post(f"/api/integrations/production-jobs/{job_id}/callback", json=payload)

    assert blocked.status_code == 409
    assert submitted.status_code == 200
    assert submitted.json()["prompt_version"] == 1
    assert callback.json()["status"] == "SUCCEEDED"
    assert callback.json()["artifact_id"]
    assert replay.json() == callback.json()


def test_invalid_artifact_is_permanently_rejected():
    created = client.post("/api/integrations/projects", json={"topic": "Invalid clip contract", "duration_seconds": 10}, headers={"Idempotency-Key": "production-create-002"})
    project_id = created.json()["project_id"]
    client.post(f"/api/integrations/projects/{project_id}/prompts/next", headers={"Idempotency-Key": "production-prompt-002"})
    client.post(f"/api/integrations/projects/{project_id}/prompts/1/approve", json={"actor": "producer"}, headers={"Idempotency-Key": "production-approval-002"})
    job = client.post(f"/api/integrations/projects/{project_id}/scenes/1/production", headers={"Idempotency-Key": "production-job-002"}).json()
    response = client.post(f"/api/integrations/production-jobs/{job['job_id']}/callback", json={"status": "SUCCEEDED", "duration_seconds": 9.5, "aspect_ratio": "16:9", "narration_end_seconds": 9.2})

    assert response.status_code == 200
    assert response.json()["status"] == "FAILED_PERMANENT"
