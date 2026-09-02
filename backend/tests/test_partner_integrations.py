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
