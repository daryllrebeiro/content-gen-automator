import pytest

from app.domain.generation import ProductionContract
from app.domain.project import ProjectInput, ProjectStatus, scene_count
from app.services.project_service import InMemoryProjectRepository, ProjectService, ProjectStateError
from app.services.narration_validator import NarrationValidationError, draft_narration
from app.services.prompt_validator import validate_prompt
from app.domain.facts import FactStatus
from app.services.fact_engine import FactEngine
from app.services.prompt_pipeline import PromptGenerationPipeline, StoryArchitect
from app.services.export_service import ExportService
from app.policies.contract import REQUIRED_PROMPT_SECTIONS, scene_count_for_duration


class FakeStructuredProvider:
    name = "fake"

    def generate_json(self, *, system_prompt, user_prompt, response_schema):
        required = set(response_schema.get("required", []))
        if "hook" in required:
            return {
                "hook": "A small beginning.",
                "central_claim": "Consistency enabled growth.",
                "ending": "The idea reached farther.",
                "scenes": [
                    {"purpose": "origin", "summary": "Show the beginning."},
                    {"purpose": "breakthrough", "summary": "Show the turning point."},
                ],
            }
        if "text" in required:
            return {"text": "One small idea can travel farther than anyone expects."}
        return {
            "story_action": "Animate the idea moving through an expanding world.",
            "camera": "Slow vertical push-in",
            "composition": "Keep the subject centered.",
            "transition": "Flow into the next scene.",
            "beats": [
                {"time_range": "0–3 seconds", "title": "Opening", "details": ["Show the beginning."]},
                {"time_range": "3–6 seconds", "title": "Growth", "details": ["Show the change."]},
                {"time_range": "6–9 seconds", "title": "Reach", "details": ["Show the wider impact."]},
                {"time_range": "9–10 seconds", "title": "Transition", "details": ["Hold for the transition."]},
            ],
        }


@pytest.mark.parametrize(
    ("duration_seconds", "expected"),
    [(10, 1), (20, 2), (30, 3)],
)
def test_scene_count(duration_seconds, expected):
    assert scene_count(duration_seconds) == expected


def test_product_contract_allows_only_supported_durations():
    assert [scene_count_for_duration(value) for value in (10, 20, 30)] == [1, 2, 3]
    try:
        scene_count_for_duration(40)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsupported duration should fail the product contract")


def test_product_contract_has_versioned_prompt_sections():
    assert "NARRATION — EXACT SCRIPT" in REQUIRED_PROMPT_SECTIONS
    assert "SAFETY AND EXCLUSIONS" in REQUIRED_PROMPT_SECTIONS


def test_project_generates_prompts_one_at_a_time():
    service = ProjectService(InMemoryProjectRepository())
    project = service.create(ProjectInput(topic="A small idea becomes global", duration_seconds=30))

    first = service.generate_next(project.id)
    assert first.scene_number == 1
    assert project.status == ProjectStatus.PROMPT_APPROVAL_PENDING
    assert "exactly 10 seconds" in first.text
    assert "CONTINUITY LOCK — MUST REMAIN IDENTICAL" in first.text
    assert "SCENE / VISUAL STORY" in first.text
    assert "NARRATION — EXACT SCRIPT" in first.text
    assert "CAPTIONS" in first.text
    assert "FINAL GENERATION REQUIREMENTS" in first.text
    assert len(first.why_this_prompt) >= 5
    assert first.quality_scores["overall"] > 0.9
    assert first.provider_name == "mock"
    assert first.model_name == "mock-v1"
    assert first.generation_latency_ms >= 0
    assert first.estimated_output_tokens > 0
    assert first.estimated_narration_seconds < 9

    service.decide_prompt(project.id, 1, decision="approved", actor="test", comment="Looks good")
    second = service.generate_next(project.id)
    service.decide_prompt(project.id, 2, decision="approved", actor="test", comment="Looks good")
    third = service.generate_next(project.id)
    assert (second.scene_number, third.scene_number) == (2, 3)
    assert project.status == ProjectStatus.PROMPT_APPROVAL_PENDING


def test_next_prompt_is_idempotent_and_cannot_exceed_scene_count():
    service = ProjectService(InMemoryProjectRepository())
    project = service.create(ProjectInput(topic="A ten second story", duration_seconds=10))

    first = service.generate_next(project.id)
    retry = service.generate_next(project.id)
    assert retry is first

    third_retry = service.generate_next(project.id)
    assert third_retry is first
    assert len(project.prompts) == 1


def test_narration_validator_rejects_long_script():
    long_script = "This sentence is intentionally much too long for a ten second animated short narration and should be rejected by the timing guardrail."
    try:
        draft_narration(long_script)
    except NarrationValidationError:
        pass
    else:
        raise AssertionError("Expected long narration to fail validation")


def test_pipeline_output_satisfies_prompt_contract():
    service = ProjectService(InMemoryProjectRepository())
    project = service.create(ProjectInput(topic="A continuity test", duration_seconds=20))
    prompt = service.generate_next(project.id)
    validate_prompt(prompt, contract=ProductionContract())
    assert "SCENE / VISUAL STORY" in prompt.text


def test_in_memory_repository_round_trip_preserves_project_state():
    repository = InMemoryProjectRepository()
    service = ProjectService(repository)
    project = service.create(ProjectInput(topic="Persistence test", duration_seconds=20))
    service.generate_next(project.id)

    restored = repository.get(project.id)
    assert restored.input.topic == "Persistence test"
    assert restored.current_scene_number == 1
    assert restored.prompts[1].scene_number == 1


def test_real_provider_pipeline_contract_with_structured_fake():
    provider = FakeStructuredProvider()
    project = ProjectInput(topic="Provider boundary", duration_seconds=20)
    from app.domain.project import Project

    domain_project = Project(input=project)
    StoryArchitect(provider).create(domain_project)
    prompt = PromptGenerationPipeline(provider).generate(domain_project, domain_project.scenes[0])
    assert prompt.narration == "One small idea can travel farther than anyone expects."
    assert "VISUAL DIRECTION" not in prompt.text
    assert "CAMERA AND COMPOSITION" in prompt.text


def test_fact_engine_is_conservative_without_verified_evidence():
    project = ProjectInput(
        topic="Fact safety",
        facts=["The event happened in 1974."],
        source_urls=["https://example.com/source"],
        duration_seconds=10,
    )
    from app.domain.project import Project

    domain_project = Project(input=project)
    claims = FactEngine().ingest(domain_project)
    assert claims[0].status == FactStatus.SOURCE_PROVIDED
    assert claims[0].approved_for_narration is False
    assert FactEngine().approved_facts(domain_project) == []


class FakeFactChecker:
    def verify_claim(self, claim, source_urls):
        claim.status = FactStatus.VERIFIED
        claim.confidence = 0.96
        claim.sources = source_urls
        claim.notes = "Verified by the test evidence provider."
        return claim


def test_fact_engine_promotes_claim_only_after_checker_verifies_it():
    from app.domain.project import Project

    domain_project = Project(input=ProjectInput(topic="Verified fact", facts=["The claim is true."], duration_seconds=10))
    claims = FactEngine(checker=FakeFactChecker()).ingest(domain_project)
    assert claims[0].status == FactStatus.VERIFIED
    assert FactEngine().approved_facts(domain_project) == ["The claim is true."]


class FailingFactChecker:
    def verify_claim(self, claim, source_urls):
        raise RuntimeError("temporary provider failure")


def test_fact_engine_fails_closed_when_evidence_provider_is_unavailable():
    from app.domain.project import Project

    domain_project = Project(input=ProjectInput(topic="Fallback", facts=["Unknown claim"], duration_seconds=10))
    claims = FactEngine(checker=FailingFactChecker()).ingest(domain_project)
    assert claims[0].status == FactStatus.UNCERTAIN
    assert FactEngine().approved_facts(domain_project) == []


def test_regeneration_preserves_scene_and_increments_version():
    service = ProjectService(InMemoryProjectRepository())
    project = service.create(ProjectInput(topic="Regeneration test", duration_seconds=20))
    original = service.generate_next(project.id)
    regenerated = service.regenerate(project.id, 1)

    assert regenerated.scene_number == original.scene_number == 1
    assert regenerated.version_number == 2
    assert project.prompts[1] is regenerated
    assert project.prompt_history[1][0].version_number == 1
    assert project.continuity.animation_style == "stylized cinematic 3D animation"


def test_regeneration_requires_an_existing_prompt():
    service = ProjectService(InMemoryProjectRepository())
    project = service.create(ProjectInput(topic="Regeneration guard", duration_seconds=10))
    try:
        service.regenerate(project.id, 1)
    except ProjectStateError:
        pass
    else:
        raise AssertionError("Expected regeneration before generation to fail")


def test_export_contains_markdown_and_publishing_package():
    service = ProjectService(InMemoryProjectRepository())
    project = service.create(ProjectInput(topic="Export test", duration_seconds=10))
    service.generate_next(project.id)
    export = ExportService()
    markdown = export.render_markdown(project)
    data = export.export_json(project)
    assert "## Publishing Package" in markdown
    assert "## Prompts" in markdown
    assert data["publishing"]["title"].startswith("Export test")
    assert data["prompts"][0]["version_number"] == 1
