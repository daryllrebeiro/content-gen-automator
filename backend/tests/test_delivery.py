from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_export_manifest_checksum_signed_download_and_delivery_are_idempotent():
    created = client.post("/api/integrations/projects", json={"topic": "A package should survive delivery retries", "duration_seconds": 10}, headers={"Idempotency-Key": "delivery-create-001"})
    project_id = created.json()["project_id"]
    generated = client.post(f"/api/integrations/projects/{project_id}/prompts/next", headers={"Idempotency-Key": "delivery-prompt-001"})
    assert generated.status_code == 200

    manifest_headers = {"Idempotency-Key": "delivery-manifest-001"}
    manifest = client.post(f"/api/integrations/projects/{project_id}/exports/manifest", headers=manifest_headers)
    replay = client.post(f"/api/integrations/projects/{project_id}/exports/manifest", headers=manifest_headers)
    payload = manifest.json()
    download = client.get(f"/api/integrations/exports/{payload['manifest_id']}/download", params={"token": payload["download_token"]})
    delivery_headers = {"Idempotency-Key": "delivery-job-001"}
    delivery = client.post(f"/api/integrations/projects/{project_id}/delivery", params={"manifest_id": payload["manifest_id"]}, headers=delivery_headers)
    delivery_replay = client.post(f"/api/integrations/projects/{project_id}/delivery", params={"manifest_id": payload["manifest_id"]}, headers=delivery_headers)

    assert manifest.status_code == 200
    assert replay.json() == payload
    assert len(payload["checksum"]) == 64
    assert download.status_code == 200
    assert download.json()["checksum"] == payload["checksum"]
    assert delivery.status_code == 200
    assert delivery_replay.json() == delivery.json()


def test_download_rejects_tampered_token():
    created = client.post("/api/integrations/projects", json={"topic": "Signed export links", "duration_seconds": 10}, headers={"Idempotency-Key": "delivery-create-002"})
    project_id = created.json()["project_id"]
    manifest = client.post(f"/api/integrations/projects/{project_id}/exports/manifest", headers={"Idempotency-Key": "delivery-manifest-002"}).json()
    response = client.get(f"/api/integrations/exports/{manifest['manifest_id']}/download", params={"token": manifest["download_token"] + "tampered"})

    assert response.status_code == 403
