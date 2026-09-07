from fastapi.testclient import TestClient
from concurrent.futures import ThreadPoolExecutor
from app.main import app

client = TestClient(app)

def test_certificate_integrity_on_empty_project_fails_with_422():
    """P0 Regression: Ensure compliance certificate cannot be issued for empty/failed projects."""
    res = client.post("/api/projects", json={"topic": "Empty Project Test", "duration_seconds": 10})
    assert res.status_code == 200
    p_id = res.json()["id"]
    owner_token = res.json()["owner_token"]

    # Request certificate on project with zero prompts
    cert_res = client.get(f"/api/projects/{p_id}/compliance-certificate", headers={"X-Project-Owner-Token": owner_token})
    assert cert_res.status_code == 422
    assert "NOT_YET_AUDITABLE" in cert_res.json()["detail"]


def test_soc2_audit_log_dynamic_and_reflects_actual_events():
    """P0 Regression: Ensure SOC2 audit log returns real, dynamic event history, not static mock events."""
    # Project 1: Only created
    res1 = client.post("/api/projects", json={"topic": "Audit Project 1", "duration_seconds": 10})
    p_id1 = res1.json()["id"]
    owner_token1 = res1.json()["owner_token"]

    # Project 2: Created, generated, and approved
    res2 = client.post("/api/projects", json={"topic": "Audit Project 2", "duration_seconds": 10})
    p_id2 = res2.json()["id"]
    owner_token2 = res2.json()["owner_token"]
    client.post(f"/api/projects/{p_id2}/generate", headers={"X-Project-Owner-Token": owner_token2})
    client.post(f"/api/projects/{p_id2}/prompts/1/approve", json={"actor": "tester"}, headers={"X-Project-Owner-Token": owner_token2, "X-Expected-Version": "2"})

    log1 = client.get(f"/api/projects/{p_id1}/audit-log/export", headers={"X-Project-Owner-Token": owner_token1}).json()
    log2 = client.get(f"/api/projects/{p_id2}/audit-log/export", headers={"X-Project-Owner-Token": owner_token2}).json()

    assert log1["project_id"] == p_id1
    assert log2["project_id"] == p_id2
    assert log1["event_count"] != log2["event_count"]
    assert log1["event_count"] == 1
    assert log1["event_records"][0]["event"] == "PROJECT_CREATED"

    events2 = [e["event"] for e in log2["event_records"]]
    assert "PROJECT_CREATED" in events2
    assert "PROMPT_GENERATED" in events2
    assert "PROMPT_APPROVED" in events2


def test_occ_header_omission_rejected_with_428():
    """P1 Regression: Ensure omitting X-Expected-Version is rejected with 428 Precondition Required."""
    res = client.post("/api/projects", json={"topic": "OCC Omission Test", "duration_seconds": 10})
    p_id = res.json()["id"]
    owner_token = res.json()["owner_token"]
    client.post(f"/api/projects/{p_id}/generate", headers={"X-Project-Owner-Token": owner_token})

    # Approve without X-Expected-Version must fail with 428
    appr_res = client.post(
        f"/api/projects/{p_id}/prompts/1/approve",
        json={"actor": "tester"},
        headers={"X-Project-Owner-Token": owner_token}
    )
    assert appr_res.status_code == 428
    assert "Precondition Required" in appr_res.json()["detail"]

    # Regenerate without X-Expected-Version must fail with 428
    regen_res = client.post(
        f"/api/projects/{p_id}/prompts/1/regenerate",
        headers={"X-Project-Owner-Token": owner_token}
    )
    assert regen_res.status_code == 428
    assert "Precondition Required" in regen_res.json()["detail"]


def test_occ_concurrent_regenerate_and_approve_rejected_with_409():
    """P1 Regression: Ensure concurrent mutating requests on same scene version conflict with 409."""
    res = client.post("/api/projects", json={"topic": "OCC Race Test", "duration_seconds": 10})
    p_id = res.json()["id"]
    owner_token = res.json()["owner_token"]
    client.post(f"/api/projects/{p_id}/generate", headers={"X-Project-Owner-Token": owner_token})

    def fire_approve():
        c = TestClient(app)
        return c.post(
            f"/api/projects/{p_id}/prompts/1/approve",
            json={"actor": "approver"},
            headers={"X-Project-Owner-Token": owner_token, "X-Expected-Version": "2"}
        )

    def fire_regenerate():
        c = TestClient(app)
        return c.post(
            f"/api/projects/{p_id}/prompts/1/regenerate",
            headers={"X-Project-Owner-Token": owner_token, "X-Expected-Version": "2"}
        )

    with ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(fire_approve)
        f2 = ex.submit(fire_regenerate)
        r1 = f1.result()
        r2 = f2.result()

    statuses = [r1.status_code, r2.status_code]
    assert 200 in statuses, f"Expected one 200 success, got {statuses}"
    assert 409 in statuses, f"Expected one 409 conflict, got {statuses}"


def test_byok_production_admission_bounded_by_concurrency_limit():
    """P1 Regression: Ensure concurrent production job admission is bounded by admission limiter."""
    res = client.post("/api/projects", json={"topic": "BYOK Admission Bound Test", "duration_seconds": 10})
    p_id = res.json()["id"]
    owner_token = res.json()["owner_token"]
    client.post(f"/api/projects/{p_id}/generate", headers={"X-Project-Owner-Token": owner_token})
    client.post(f"/api/projects/{p_id}/prompts/1/approve", json={"actor": "tester"}, headers={"X-Project-Owner-Token": owner_token, "X-Expected-Version": "2"})

    def fire_prod(i):
        c = TestClient(app)
        return c.post(
            f"/api/projects/{p_id}/scenes/1/production",
            headers={
                "X-Project-Owner-Token": owner_token,
                "Idempotency-Key": f"test-prod-adm-{i}",
                "X-Runway-API-Key": "rw_test_key"
            }
        )

    with ThreadPoolExecutor(max_workers=10) as ex:
        statuses = list(ex.map(fire_prod, range(10)))
    
    status_codes = [r.status_code for r in statuses]
    # Bound is 3: at most 3 admitted with 200, rest rejected with 429
    assert status_codes.count(200) <= 3
    assert status_codes.count(429) >= 7
