import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.adapters.grafana_telemetry import telemetry
from app.adapters.parallel_search import parallel_search
from app.adapters.clickhouse_analytics import clickhouse_analytics
from app.adapters.ibm_governance import ibm_governance

client = TestClient(app)

def test_partner_ecosystem_status_endpoint():
    response = client.get("/api/partners/status")
    assert response.status_code == 200
    data = response.json()
    assert data["hackathon"] == "Agentic Cinema: The Blockbuster Hackathon"
    assert "grafana_labs" in data["partners"]
    assert "replit" in data["partners"]
    assert "parallel" in data["partners"]
    assert "clickhouse" in data["partners"]
    assert "ibm_watsonx" in data["partners"]


def test_grafana_metrics_endpoint():
    telemetry.record_project_created("Sci-fi Space Odyssey")
    telemetry.record_prompt_generation(0.45, input_tokens=300, output_tokens=150)
    telemetry.record_governance_check("passed")
    
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    text = response.text
    assert "agent_projects_created_total" in text
    assert "agent_tokens_consumed_total" in text
    assert "ibm_governance_verifications_total" in text


def test_parallel_search_research_endpoint():
    response = client.post(
        "/api/research/parallel",
        json={"topic": "Bioluminescence in deep sea", "tone": "curious documentary"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["partner"] == "Parallel"
    assert len(data["verified_facts"]) > 0
    assert len(data["visual_references"]) > 0
    assert "audience_hook" in data


def test_clickhouse_analytics_logging_and_summary():
    clickhouse_analytics.log_event("test_render_event", "test-project-123", {"fps": 30}, duration_ms=120.5)
    summary = clickhouse_analytics.get_analytics_summary()
    assert summary["partner"] == "ClickHouse"
    assert summary["total_events_recorded"] > 0
    
    response = client.get("/api/analytics/clickhouse")
    assert response.status_code == 200
    assert response.json()["partner"] == "ClickHouse"


def test_ibm_governance_audit():
    clean_audit = ibm_governance.audit_prompt("A breathtaking visual of underwater creatures glowing gently.")
    assert "IBM watsonx" in clean_audit["partner"]
    assert clean_audit["decision"] == "passed"
    assert clean_audit["risk_score"] < 0.1

    flagged_audit = ibm_governance.audit_prompt("Extreme violence and trademark_infringement against brand.")
    assert flagged_audit["decision"] == "flagged"
    assert flagged_audit["risk_score"] > 0.5


def test_full_project_lifecycle_triggers_partner_telemetry():
    # 1. Create project
    created = client.post(
        "/api/projects",
        json={
            "topic": "The Secret Life of Neon City",
            "facts": ["Cyberpunk aesthetic blends neon and noir."],
            "duration_seconds": 30,
            "tone": "cyberpunk cinematic",
            "visual_preferences": {"style": "stylized 3D neon glow"},
        },
    )
    assert created.status_code == 200
    project_id = created.json()["id"]

    # 2. Generate prompt (triggers Grafana, IBM, ClickHouse)
    gen = client.post(f"/api/projects/{project_id}/generate")
    assert gen.status_code == 200

    # 3. Verify telemetry collected
    status_res = client.get("/api/partners/status")
    status = status_res.json()["partners"]
    assert status["grafana_labs"]["projects_created"] >= 1
    assert status["clickhouse"]["total_events_recorded"] >= 1


def test_compliance_certificate_endpoint():
    # Create project and generate prompt
    created = client.post(
        "/api/projects",
        json={"topic": "Quantum Computing Frontiers", "duration_seconds": 10},
    )
    assert created.status_code == 200
    project_id = created.json()["id"]
    client.post(f"/api/projects/{project_id}/generate")

    # Fetch live compliance certificate
    cert_res = client.get(f"/api/projects/{project_id}/compliance-certificate")
    assert cert_res.status_code == 200
    cert = cert_res.json()
    assert cert["governance_provider"] == "IBM watsonx.governance"
    assert cert["is_signature_valid"] is True
    assert cert["signature_algorithm"] == "HMAC-SHA256"


def test_governance_violation_halts_generation():
    bad_created = client.post(
        "/api/projects",
        json={"topic": "Extreme violence and trademark_infringement against brand", "duration_seconds": 10},
    )
    assert bad_created.status_code == 200
    bad_id = bad_created.json()["id"]
    
    # Generation must be halted by IBM watsonx governance gate with 422
    bad_gen = client.post(f"/api/projects/{bad_id}/generate")
    assert bad_gen.status_code == 422
    assert "IBM watsonx.governance safety violation" in bad_gen.json()["detail"]


def test_cost_ceiling_enforcement_halts_production():
    # Create project with low token ceiling of 100 tokens
    res = client.post(
        "/api/projects",
        json={"topic": "Deep Sea Science Mysteries", "duration_seconds": 10, "token_budget": 100},
    )
    assert res.status_code == 200
    p_id = res.json()["id"]

    # Generate prompt (generates ~400 tokens, which exceeds the 100 ceiling)
    gen = client.post(f"/api/projects/{p_id}/generate")
    assert gen.status_code == 200
    
    # Approve prompt
    appr = client.post(f"/api/projects/{p_id}/prompts/1/approve", json={"decision": "APPROVE", "actor": "director"})
    assert appr.status_code == 200

    # Submitting production job must fail with HTTP 429 Cost Ceiling Exceeded
    prod_res = client.post(f"/api/projects/{p_id}/scenes/1/production")
    assert prod_res.status_code == 429
    assert "Cost ceiling exceeded" in prod_res.json()["detail"]


def test_policy_packs_api_list_and_create():
    list_res = client.get("/api/governance/policy-packs")
    assert list_res.status_code == 200
    packs = list_res.json()
    assert len(packs) >= 3
    pack_ids = [p["id"] for p in packs]
    assert "general_audience" in pack_ids
    assert "kids_family" in pack_ids

    # Create custom policy pack
    create_res = client.post(
        "/api/governance/policy-packs",
        json={
            "id": "custom_enterprise_strict",
            "name": "Custom Enterprise Strict",
            "description": "Zero tolerance for competitor trademarks.",
            "max_risk_score_allowed": 0.08,
            "allow_mild_action": False,
            "copyright_strictness": "strict"
        }
    )
    assert create_res.status_code == 200
    assert create_res.json()["id"] == "custom_enterprise_strict"


def test_governance_advisor_mode():
    # Advisory on safe text
    safe_res = client.post(
        "/api/governance/advisor",
        json={"prompt_text": "Bioluminescent creatures glowing gently in the dark ocean.", "policy_pack": "general_audience"}
    )
    assert safe_res.status_code == 200
    assert safe_res.json()["decision"] == "passed"
    assert safe_res.json()["is_safe_to_submit"] is True

    # Advisory on trademark/sensitive text
    risky_res = client.post(
        "/api/governance/advisor",
        json={"prompt_text": "Mickey Mouse trademark_infringement with weapons.", "policy_pack": "kids_family"}
    )
    assert risky_res.status_code == 200
    assert risky_res.json()["decision"] == "flagged"
    assert risky_res.json()["is_safe_to_submit"] is False


def test_tamper_evident_certificate_verification():
    # Create project and fetch real signed certificate
    created = client.post("/api/projects", json={"topic": "Bioluminescence 2026", "duration_seconds": 10})
    p_id = created.json()["id"]
    client.post(f"/api/projects/{p_id}/generate")

    cert = client.get(f"/api/projects/{p_id}/compliance-certificate").json()

    # 1. Authentic certificate must pass verification
    verify_res = client.post("/api/governance/verify-certificate", json=cert)
    assert verify_res.status_code == 200
    assert verify_res.json()["is_valid"] is True
    assert verify_res.json()["verdict"] == "AUTHENTIC_VERIFIED"

    # 2. Tampered certificate (modified topic or payload) must fail
    tampered_cert = dict(cert)
    tampered_cert["topic"] = "TAMPERED_INJECTED_TOPIC"
    tampered_res = client.post("/api/governance/verify-certificate", json=tampered_cert)
    assert tampered_res.status_code == 200
    # Because signature hash was computed over the canonical payload, if canonical_payload is modified or given_signature doesn't match:
    tampered_cert["canonical_payload"] = "cert:tampered:tampered:1:timestamp"
    tampered_res2 = client.post("/api/governance/verify-certificate", json=tampered_cert)
    assert tampered_res2.json()["is_valid"] is False
    assert tampered_res2.json()["verdict"] == "TAMPER_DETECTED_INVALID"


def test_budget_status_endpoint():
    created = client.post("/api/projects", json={"topic": "Deep Space Physics", "duration_seconds": 10, "token_budget": 25000})
    p_id = created.json()["id"]

    res = client.get(f"/api/telemetry/budget-status/{p_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["token_budget"] == 25000
    assert data["tokens_consumed"] >= 0
    assert data["budget_headroom"] <= 25000
    assert data["cost_ceiling_exceeded"] is False


