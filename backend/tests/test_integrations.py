from fastapi.testclient import TestClient

from app.api.routes import project_service
from app.main import app


client = TestClient(app)


def _payload(topic: str = "A small invention becomes a worldwide chain") -> dict:
    return {"topic": topic, "duration_seconds": 30}


def test_integration_create_is_idempotent_and_emits_audit_event():
    key = "integration-test-create-001"
    response = client.post("/api/integrations/projects", json=_payload(), headers={"Idempotency-Key": key, "X-Request-ID": "request-001"})
    replay = client.post("/api/integrations/projects", json=_payload(), headers={"Idempotency-Key": key, "X-Request-ID": "request-002"})

    assert response.status_code == 200
    assert response.json()["created"] is True
    assert replay.status_code == 200
    assert replay.json()["created"] is False
    assert replay.json()["project_id"] == response.json()["project_id"]
    assert any(event.event_type == "integration.project_create" and event.request_id == "request-001" for event in project_service.repository.audit_events)


def test_integration_create_rejects_idempotency_key_payload_mismatch():
    key = "integration-test-create-002"
    client.post("/api/integrations/projects", json=_payload(), headers={"Idempotency-Key": key})
    response = client.post("/api/integrations/projects", json=_payload("A different idea"), headers={"Idempotency-Key": key})

    assert response.status_code == 409


def test_integration_create_requires_idempotency_key():
    response = client.post("/api/integrations/projects", json=_payload())

    assert response.status_code == 422
