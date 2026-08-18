from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_fact_verification_job_is_idempotent_and_fails_closed_without_provider():
    created = client.post(
        "/api/integrations/projects",
        json={"topic": "A claim needs careful evidence", "facts": ["A claim supplied by the user."], "source_urls": ["https://example.org/source"], "duration_seconds": 10},
        headers={"Idempotency-Key": "evidence-create-001"},
    )
    project_id = created.json()["project_id"]
    headers = {"Idempotency-Key": "evidence-verify-001", "X-Request-ID": "evidence-request-001"}
    first = client.post(f"/api/integrations/projects/{project_id}/facts/verify", headers=headers)
    replay = client.post(f"/api/integrations/projects/{project_id}/facts/verify", headers=headers)
    status = client.get(f"/api/integrations/fact-verification-jobs/{first.json()['job_id']}")

    assert first.status_code == 200
    assert first.json()["status"] == "FAILED_RETRYABLE"
    assert replay.json() == first.json()
    assert status.json()["job_id"] == first.json()["job_id"]


def test_fact_verification_key_rejects_payload_scope_reuse():
    first = client.post("/api/integrations/projects", json={"topic": "Evidence topic one", "duration_seconds": 10}, headers={"Idempotency-Key": "evidence-create-002"})
    second = client.post("/api/integrations/projects", json={"topic": "Evidence topic two", "duration_seconds": 10}, headers={"Idempotency-Key": "evidence-create-003"})
    key = "evidence-verify-002"
    client.post(f"/api/integrations/projects/{first.json()['project_id']}/facts/verify", headers={"Idempotency-Key": key})
    response = client.post(f"/api/integrations/projects/{second.json()['project_id']}/facts/verify", headers={"Idempotency-Key": key})

    assert response.status_code == 409
