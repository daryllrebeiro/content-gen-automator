import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def main() -> None:
    client = TestClient(app)
    readiness = client.get("/ready")
    readiness.raise_for_status()

    created = client.post(
        "/api/projects",
        json={
            "topic": "How a small discovery became globally important",
            "facts": [],
            "duration_seconds": 30,
            "tone": "curious cinematic documentary",
            "visual_preferences": {"style": "stylized cinematic 3D animation"},
        },
    )
    created.raise_for_status()
    project_id = created.json()["id"]

    prompts = []
    for scene_number in range(1, 4):
        response = client.post(f"/api/projects/{project_id}/prompts/next")
        response.raise_for_status()
        prompts.append(response.json())
        approval = client.post(
            f"/api/integrations/projects/{project_id}/prompts/{scene_number}/approve",
            json={"actor": "smoke-test", "comment": "Approved by smoke test."},
            headers={"Idempotency-Key": f"smoke-approval-{scene_number}"},
        )
        approval.raise_for_status()

    regenerated = client.post(f"/api/projects/{project_id}/prompts/1/regenerate")
    regenerated.raise_for_status()
    export = client.get(f"/api/projects/{project_id}/export")
    export.raise_for_status()

    print("Smoke test passed")
    print(f"provider={readiness.json()['provider']}")
    print(f"repository={readiness.json()['repository']}")
    print(f"scenes={len(prompts)}")
    print(f"scene_1_regenerated_version={regenerated.json()['version_number']}")
    print(f"export_markdown_characters={len(export.json()['markdown'])}")


if __name__ == "__main__":
    main()
