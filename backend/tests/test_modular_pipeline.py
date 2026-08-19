import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.domain.project import ProjectInput

client = TestClient(app)

def test_project_input_provider_fields():
    # Verify ProjectInput defaults and assignments
    inp = ProjectInput(
        topic="Test topic",
        duration_seconds=10,
        tts_provider="elevenlabs",
        video_provider="runway",
        stitch_provider="ffmpeg",
        publish_provider="youtube"
    )
    assert inp.tts_provider == "elevenlabs"
    assert inp.video_provider == "runway"
    assert inp.stitch_provider == "ffmpeg"
    assert inp.publish_provider == "youtube"


def test_create_project_with_custom_providers():
    # Call public API to create project with custom providers
    payload = {
        "topic": "Test modular project with custom providers",
        "facts": ["Modular block 1", "Modular block 2"],
        "duration_seconds": 20,
        "autonomous": True,
        "tts_provider": "elevenlabs",
        "video_provider": "kling",
        "stitch_provider": "ffmpeg",
        "publish_provider": "youtube"
    }
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["tts_provider"] == "elevenlabs"
    assert data["video_provider"] == "kling"
    assert data["stitch_provider"] == "ffmpeg"
    assert data["publish_provider"] == "youtube"


def test_production_pipeline_mock_fallback():
    # Verify that if providers are set to runway/elevenlabs but keys are missing,
    # the async task catches the error and marks the production job as FAILED_PERMANENT
    payload = {
        "topic": "Missing API keys test project",
        "duration_seconds": 10,
        "tts_provider": "elevenlabs",
        "video_provider": "runway",
    }
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 200
    proj_id = response.json()["id"]

    # 1. Generate prompt for scene 1
    gen_resp = client.post(f"/api/projects/{proj_id}/prompts/next")
    assert gen_resp.status_code == 200

    # 2. Approve prompt for scene 1
    app_resp = client.post(f"/api/projects/{proj_id}/prompts/1/approve", json={"actor": "user", "comment": "looks good"})
    assert app_resp.status_code == 200

    # 3. Submit production clip (which triggers background tasks)
    # Since there are no keys in tests, it will fall back to error state
    prod_resp = client.post(f"/api/projects/{proj_id}/scenes/1/production")
    assert prod_resp.status_code == 200
    job_id = prod_resp.json()["job_id"]

    # Let the background task run (since it's a TestClient with background tasks,
    # we can access the jobs synchronously or wait. FastAPI TestClient runs background tasks
    # synchronously on response close, so the task has already executed!)
    jobs_resp = client.get(f"/api/projects/{proj_id}/production-jobs")
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "FAILED_PERMANENT"
    assert "ELEVENLABS_API_KEY is not configured" in jobs[0]["error"]
