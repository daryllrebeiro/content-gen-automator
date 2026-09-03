from app.services.model_tier_service import ModelTierService
from app.agents.screenwriter_agent import screenwriter_agent
from app.agents.orchestrator_agent import orchestrator_agent

def test_model_tier_service_catalog():
    tiers = ModelTierService.list_tiers()
    tier_ids = [t["id"] for t in tiers]
    assert "fast_draft" in tier_ids
    assert "flagship" in tier_ids

    fast = ModelTierService.get_tier_spec("fast_draft")
    assert fast.screenwriter_model == "gemma-2-9b-it"
    assert fast.cinematographer_model == "gemini-2.5-flash"
    assert fast.governance_model == "gemini-2.5-flash"
    assert fast.estimated_cost_per_draft < 0.0005

    flagship = ModelTierService.get_tier_spec("flagship")
    assert flagship.screenwriter_model == "gemini-2.5-flash"

def test_screenwriter_agent_fast_draft_tier():
    facts = ["Hydrothermal vents support chemosynthesis in the deep ocean."]
    result = screenwriter_agent.draft_narration(
        scene_number=1,
        total_scenes=3,
        topic="Deep Sea Ecology",
        facts=facts,
        target_seconds=10,
        model_tier="fast_draft"
    )
    assert result["agent"] == "ScreenwriterAgent"
    assert result["model"] == "gemma-2-9b-it"
    assert result["model_tier"] == "fast_draft"
    assert result["estimated_cost_usd"] == 0.0002
    assert result["estimated_latency_ms"] == 950.0

def test_screenwriter_agent_flagship_tier():
    facts = ["Hydrothermal vents support chemosynthesis in the deep ocean."]
    result = screenwriter_agent.draft_narration(
        scene_number=1,
        total_scenes=3,
        topic="Deep Sea Ecology",
        facts=facts,
        target_seconds=10,
        model_tier="flagship"
    )
    assert result["agent"] == "ScreenwriterAgent"
    assert result["model"] == "gemini-2.5-flash"
    assert result["model_tier"] == "flagship"
    assert result["estimated_cost_usd"] == 0.0010
    assert result["estimated_latency_ms"] == 2400.0

def test_orchestrator_routes_model_tier():
    facts = ["Saturn's rings are composed of 99% pure water ice."]
    trace = orchestrator_agent.orchestrate_scene_generation(
        project_id="test_proj_routing",
        topic="Saturn Rings",
        scene_number=1,
        total_scenes=1,
        facts=facts,
        model_tier="fast_draft"
    )
    assert "OrchestratorAgent" in trace["orchestrator"]
    assert trace["script_metadata"]["model"] == "gemma-2-9b-it"
    assert trace["script_metadata"]["model_tier"] == "fast_draft"
