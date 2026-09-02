import pytest
from app.agents.orchestrator_agent import orchestrator_agent
from app.agents.research_agent import research_agent
from app.agents.screenwriter_agent import screenwriter_agent
from app.agents.cinematographer_agent import cinematographer_agent
from app.agents.continuity_agent import continuity_agent
from app.agents.governance_agent import governance_agent
from app.agents.publishing_agent import publishing_agent
from app.services.policy_pack_service import policy_pack_service
from app.services.compliance_certificate_service import compliance_certificate_service
from app.services.localization_service import localization_service
from app.services.brand_kit_service import brand_kit_service

def test_research_agent_grounding():
    result = research_agent.ground_topic("Deep Sea Bioluminescence", "curious documentary")
    assert result["agent"] == "ResearchAgent"
    assert len(result["facts"]) > 0
    assert len(result["visual_references"]) > 0
    assert "audience_hook" in result


def test_screenwriter_agent_pacing():
    script = screenwriter_agent.draft_narration(
        scene_number=1,
        total_scenes=3,
        topic="Volcanoes",
        facts=["Volcanoes form from magma rising from the mantle."],
        target_seconds=10
    )
    assert script["agent"] == "ScreenwriterAgent"
    assert script["word_count"] > 0
    assert script["pacing_status"] in {"optimal", "adjusted"}


def test_cinematographer_agent_directives():
    visual = cinematographer_agent.synthesize_visual_prompt(
        scene_number=1,
        topic="Cyberpunk Tokyo",
        narration="Neon reflections bounce across the wet asphalt.",
        visual_style="stylized 3D neon glow"
    )
    assert visual["agent"] == "CinematographerAgent"
    assert "Cinematic 4K" in visual["visual_prompt"]
    assert visual["camera_directive"] is not None


def test_continuity_agent_memory_lock():
    lock = continuity_agent.get_continuity_lock("studio_default", scene_number=2)
    assert lock["agent"] == "ContinuityAgent"
    assert lock["seed"] in [42, 1337, 8080]


def test_governance_agent_dual_pass_audit():
    audit = governance_agent.audit_scene(
        visual_prompt="A breathtaking crystal cave glowing with sapphire crystals.",
        narration="Inside this cave, crystals have grown undisturbed for millions of years.",
        facts=["Crystals grew over millions of years."]
    )
    assert audit["agent"] == "GovernanceAgent"
    assert audit["decision"] == "passed"
    assert audit["risk_score"] < 0.15


def test_orchestrator_agent_a2a_handoff_sequence():
    result = orchestrator_agent.orchestrate_scene_generation(
        project_id="test-proj-001",
        topic="The Secret World of Coral Reefs",
        scene_number=1,
        total_scenes=3
    )
    assert "OrchestratorAgent" in result["orchestrator"]
    assert result["scene_number"] == 1
    assert "narration" in result
    assert "visual_prompt" in result
    assert result["governance_decision"] == "passed"
    assert "a2a_trace" in result
    assert len(result["a2a_trace"]) == 5


def test_policy_pack_service():
    packs = policy_pack_service.list_policy_packs()
    assert len(packs) >= 3
    kids_pack = policy_pack_service.get_policy_pack("kids_family")
    assert kids_pack.max_risk_score_allowed == 0.05


def test_compliance_certificate_generation_and_tamper_verification():
    cert = compliance_certificate_service.generate_certificate(
        project_id="proj-999",
        topic="Ancient Egyptian Pyramids",
        policy_pack_id="general_audience",
        audit_records=[{"scene_number": 1, "decision": "passed", "risk_score": 0.02}],
        manifest_id="manifest-999"
    )
    assert cert["overall_compliance_verdict"] == "CERTIFIED_COMPLIANT"
    assert "CERT-IBM-GOV" in cert["certificate_id"]
    assert len(cert["signature_hash"]) == 64
    
    # 1. Valid signature passes verification
    assert compliance_certificate_service.verify_certificate(cert) is True

    # 2. Tampered signature fails verification
    tampered_cert = dict(cert)
    tampered_cert["signature_hash"] = "0" * 64
    assert compliance_certificate_service.verify_certificate(tampered_cert) is False


def test_policy_pack_differential_outcomes():
    from app.adapters.ibm_governance import ibm_governance
    
    # Prompt with slightly spooky terms for kids pack
    test_prompt = "A scary monster prowls through the dark abyss of shadows."
    
    general_audit = ibm_governance.audit_prompt(test_prompt, policy_pack="general_audience")
    kids_audit = ibm_governance.audit_prompt(test_prompt, policy_pack="kids_family")
    
    assert kids_audit["decision"] == "flagged"
    assert "Flagged" in kids_audit["policy_checks"]["brand_safety"]


def test_localization_service():
    localized = localization_service.localize_project(
        project_id="proj-es",
        topic="Deep Space Telescopes",
        narration_en="Telescopes reveal distant galaxies.",
        target_locale="es-ES"
    )
    assert localized["target_locale"] == "es-ES"
    assert "¿Sabías" in localized["translated_narration"]
    assert localized["locale_governance_decision"] == "passed"


def test_brand_kit_service():
    kit = brand_kit_service.get_brand_kit("studio_default")
    assert kit.studio_name == "Agentic Cinema Studio"
    assert kit.watermark_position == "top_right"
