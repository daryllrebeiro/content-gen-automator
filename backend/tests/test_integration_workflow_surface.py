from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_integration_status_and_prompt_next_are_idempotent():
    headers = {"Idempotency-Key": "workflow-create-001", "X-Request-ID": "n8n-exec-001"}
    created = client.post("/api/integrations/projects", json={"topic": "A local idea reaches the world", "duration_seconds": 10}, headers=headers)
    project_id = created.json()["project_id"]

    status = client.get(f"/api/integrations/projects/{project_id}/status", headers={"X-Request-ID": "n8n-exec-001"})
    prompt_headers = {"Idempotency-Key": "workflow-prompt-001", "X-Request-ID": "n8n-exec-001"}
    prompt = client.post(f"/api/integrations/projects/{project_id}/prompts/next", headers=prompt_headers)
    replay = client.post(f"/api/integrations/projects/{project_id}/prompts/next", headers=prompt_headers)

    assert status.status_code == 200
    assert status.json()["next_scene_number"] == 1
    assert prompt.status_code == 200
    assert prompt.json()["prompt"]["scene_number"] == 1
    assert replay.status_code == 200
    assert replay.json()["prompt"]["scene_number"] == 1


def test_integration_prompt_next_requires_idempotency_key():
    created = client.post("/api/integrations/projects", json={"topic": "A local idea reaches the world", "duration_seconds": 10}, headers={"Idempotency-Key": "workflow-create-002"})
    response = client.post(f"/api/integrations/projects/{created.json()['project_id']}/prompts/next")

    assert response.status_code == 422
