import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from app.main import app
from app.adapters.grafana_telemetry import telemetry

client = TestClient(app)


def test_m1_unprotected_platform_export_download_route():
    """Finding M-1: Unauthenticated platform-export download must return 403."""
    res = client.post("/api/projects", json={"topic": "Export Test M1", "duration_seconds": 10, "target_platforms": ["TIKTOK"]})
    assert res.status_code == 200
    proj_id = res.json()["id"]
    owner_token = res.json()["owner_token"]

    # Unauthenticated GET download -> 403
    unauthed = client.get(
        f"/api/projects/{proj_id}/platform-exports/tiktok/download/manifest.json",
        headers={"Skip-Auto-Owner-Token": "true"}
    )
    assert unauthed.status_code == 403, f"Expected 403, got {unauthed.status_code}: {unauthed.text}"
    assert "Access denied" in unauthed.json()["detail"]


def test_q1_cost_ceiling_race_condition_at_boundary():
    """Finding Q-1: Concurrency at boundary and atomic reservation."""
    res = client.post("/api/projects", json={"topic": "Cost Boundary Test Q1", "duration_seconds": 10, "token_budget": 5000})
    proj_id = res.json()["id"]
    owner_token = res.json()["owner_token"]
    client.post(f"/api/projects/{proj_id}/generate", headers={"X-Project-Owner-Token": owner_token})
    client.post(f"/api/projects/{proj_id}/prompts/1/approve", json={"actor": "tester"}, headers={"X-Project-Owner-Token": owner_token})

    # At exact boundary (5000 == 5000): all 10 concurrent requests must be rejected with 429
    telemetry.project_tokens[str(proj_id)] = 5000

    def fire_prod(i):
        c = TestClient(app)
        return c.post(
            f"/api/projects/{proj_id}/scenes/1/production",
            headers={"X-Project-Owner-Token": owner_token, "Idempotency-Key": f"q1-job-{i}"}
        )

    with ThreadPoolExecutor(max_workers=10) as ex:
        statuses = [r.status_code for r in ex.map(fire_prod, range(10))]
    assert all(s == 429 for s in statuses), f"Expected all 429 at budget ceiling, got {statuses}"

    # Near boundary (4900/5000 with 100 token reservation): exactly 1 succeeds, 9 rejected with 429
    telemetry.project_tokens[str(proj_id)] = 4900
    with ThreadPoolExecutor(max_workers=10) as ex:
        boundary_statuses = [r.status_code for r in ex.map(lambda i: fire_prod(i + 20), range(10))]
    assert boundary_statuses.count(200) == 1, f"Expected 1 success, got {boundary_statuses.count(200)}"
    assert boundary_statuses.count(429) == 9, f"Expected 9 rate limited, got {boundary_statuses.count(429)}"


def test_q3_approve_reject_split_brain_occ():
    """Finding Q-3: Optimistic concurrency control on decide_prompt prevents split-brain."""
    res = client.post("/api/projects", json={"topic": "OCC Split Brain Test Q3", "duration_seconds": 10})
    proj_id = res.json()["id"]
    owner_token = res.json()["owner_token"]
    gen_res = client.post(f"/api/projects/{proj_id}/generate", headers={"X-Project-Owner-Token": owner_token})
    assert gen_res.status_code == 200

    # Both reviewers read the project at this exact version
    proj_res = client.get(f"/api/projects/{proj_id}", headers={"X-Project-Owner-Token": owner_token})
    expected_ver = proj_res.json()["version"]

    def fire_approve():
        c = TestClient(app)
        return c.post(
            f"/api/projects/{proj_id}/prompts/1/approve",
            json={"actor": "approver", "comment": "looks good"},
            headers={"X-Project-Owner-Token": owner_token, "X-Expected-Version": str(expected_ver)}
        )

    def fire_reject():
        c = TestClient(app)
        return c.post(
            f"/api/projects/{proj_id}/prompts/1/reject",
            json={"actor": "rejecter", "comment": "redo this"},
            headers={"X-Project-Owner-Token": owner_token, "X-Expected-Version": str(expected_ver)}
        )

    with ThreadPoolExecutor(max_workers=2) as ex:
        f_app = ex.submit(fire_approve)
        f_rej = ex.submit(fire_reject)
        r_app = f_app.result()
        r_rej = f_rej.result()

    # One must succeed with 200, one must fail with 409 Conflict
    assert (r_app.status_code == 200 and r_rej.status_code == 409) or (r_app.status_code == 409 and r_rej.status_code == 200), \
        f"Expected (200, 409) or (409, 200), got {r_app.status_code} and {r_rej.status_code}"


def test_n3_project_existence_oracle_uniform_403():
    """Finding N-3: Project-existence oracle eliminated (uniform 403 on real vs nonexistent)."""
    res = client.post("/api/projects", json={"topic": "Oracle Test N3", "duration_seconds": 10})
    real_id = res.json()["id"]
    nonexistent_id = str(uuid.uuid4())

    r_nonexistent = client.get(f"/api/projects/{nonexistent_id}")
    r_real_no_token = client.get(f"/api/projects/{real_id}", headers={"Skip-Auto-Owner-Token": "true"})
    r_nonexistent_wrong_token = client.get(f"/api/projects/{nonexistent_id}", headers={"X-Project-Owner-Token": "bad-token"})
    r_real_wrong_token = client.get(f"/api/projects/{real_id}", headers={"X-Project-Owner-Token": "bad-token"})

    assert r_nonexistent.status_code == 403
    assert r_real_no_token.status_code == 403
    assert r_nonexistent_wrong_token.status_code == 403
    assert r_real_wrong_token.status_code == 403
    assert r_nonexistent.json() == r_real_no_token.json()
    assert r_nonexistent_wrong_token.json() == r_real_wrong_token.json()


def test_n2_idempotency_support_on_project_create():
    """Finding N-2: Idempotency-Key support on POST /api/projects returns identical project."""
    idemp_key = f"n2-idemp-{uuid.uuid4()}"
    payload = {"topic": "Idempotent Project Create N2", "duration_seconds": 10, "tone": "cinematic"}

    resp1 = client.post("/api/projects", json=payload, headers={"Idempotency-Key": idemp_key})
    resp2 = client.post("/api/projects", json=payload, headers={"Idempotency-Key": idemp_key})

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["id"] == resp2.json()["id"]
    assert resp1.json()["owner_token"] == resp2.json()["owner_token"]


def test_r2_provider_key_mismatch_upfront_rejection():
    """Finding R-2: Silent provider-key mismatch rejected upfront with 400."""
    res = client.post("/api/projects", json={"topic": "Kling with Runway Key R2", "duration_seconds": 10, "video_provider": "kling"})
    proj_id = res.json()["id"]
    owner_token = res.json()["owner_token"]
    client.post(f"/api/projects/{proj_id}/generate", headers={"X-Project-Owner-Token": owner_token})
    client.post(f"/api/projects/{proj_id}/prompts/1/approve", json={"actor": "tester"}, headers={"X-Project-Owner-Token": owner_token})

    # Submit production clip providing Runway key for Kling provider
    resp = client.post(
        f"/api/projects/{proj_id}/scenes/1/production",
        headers={
            "X-Project-Owner-Token": owner_token,
            "X-Runway-API-Key": "rw_live_test_key_12345"
        }
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["error"] == "BYOK_KEY_REQUIRED"
    assert detail["provider"] == "kling"


def test_m2_single_canonical_policy_pack_route():
    """Finding M-2: Redundant policy pack route removed from main.py, canonical in routes.py."""
    import inspect
    from app import main
    main_source = inspect.getsource(main)
    assert "@app.get(\"/api/governance/policy-packs\")" not in main_source

    schema = app.openapi()
    assert "/api/governance/policy-packs" in schema["paths"]
