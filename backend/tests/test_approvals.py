from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_approval_is_required_before_next_scene_and_rejection_is_audited():
    create = client.post("/api/integrations/projects", json={"topic": "A small idea becomes a global chain", "duration_seconds": 20}, headers={"Idempotency-Key": "approval-create-001"})
    project_id = create.json()["project_id"]
    prompt_headers = {"Idempotency-Key": "approval-prompt-001"}
    client.post(f"/api/integrations/projects/{project_id}/prompts/next", headers=prompt_headers)

    blocked = client.post(f"/api/integrations/projects/{project_id}/prompts/next", headers={"Idempotency-Key": "approval-prompt-002"})
    rejected = client.post(f"/api/integrations/projects/{project_id}/prompts/1/reject", json={"actor": "editor", "comment": "Clarify the opening."}, headers={"Idempotency-Key": "approval-reject-001"})
    approved = client.post(f"/api/integrations/projects/{project_id}/prompts/1/approve", json={"actor": "editor", "comment": "Approved after review."}, headers={"Idempotency-Key": "approval-approve-001"})
    next_prompt = client.post(f"/api/integrations/projects/{project_id}/prompts/next", headers={"Idempotency-Key": "approval-prompt-002"})

    assert blocked.status_code == 409
    assert rejected.status_code == 200
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert next_prompt.status_code == 200
    assert next_prompt.json()["prompt"]["scene_number"] == 2


def test_approval_replay_is_idempotent():
    create = client.post("/api/integrations/projects", json={"topic": "A small idea becomes a global chain", "duration_seconds": 10}, headers={"Idempotency-Key": "approval-create-002"})
    project_id = create.json()["project_id"]
    client.post(f"/api/integrations/projects/{project_id}/prompts/next", headers={"Idempotency-Key": "approval-prompt-003"})
    headers = {"Idempotency-Key": "approval-approve-002"}
    body = {"actor": "editor", "comment": "Approved."}
    first = client.post(f"/api/integrations/projects/{project_id}/prompts/1/approve", json=body, headers=headers)
    replay = client.post(f"/api/integrations/projects/{project_id}/prompts/1/approve", json=body, headers=headers)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json() == first.json()
