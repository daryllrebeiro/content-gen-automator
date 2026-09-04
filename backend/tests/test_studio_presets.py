from app.services.studio_preset_service import studio_preset_service
from app.domain.project import ProjectInput, Platform

def test_studio_preset_service_defaults():
    presets = studio_preset_service.list_presets()
    preset_ids = [p["id"] for p in presets]
    assert "fast_youtube_draft" in preset_ids
    assert "multi_platform_viral" in preset_ids
    assert "enterprise_compliance_launch" in preset_ids

def test_custom_preset_creation():
    data = {
        "id": "my_custom_preset",
        "name": "My Custom Studio Preset",
        "target_platforms": ["YOUTUBE_SHORTS", "TIKTOK"],
        "video_provider": "kling",
        "model_tier": "fast_draft",
        "policy_pack_id": "kids_family",
        "suggested_topic": "Robotics in 2030"
    }
    preset = studio_preset_service.create_custom_preset(data)
    assert preset.id == "my_custom_preset"
    assert preset.video_provider == "kling"
    assert preset.model_tier == "fast_draft"
    assert not preset.is_system_preset

    retrieved = studio_preset_service.get_preset("my_custom_preset")
    assert retrieved is not None
    assert retrieved.name == "My Custom Studio Preset"

def test_preset_vs_manual_full_domain_object_deep_diff_empty():
    """Adversarially diff all domain fields between preset-instantiated Project and manual Project."""
    from uuid import UUID
    from app.domain.project import Project

    preset = studio_preset_service.get_preset("multi_platform_viral")
    assert preset is not None

    fixed_id = UUID("11111111-2222-3333-4444-555555555555")

    # Project from preset
    proj_preset = Project(
        id=fixed_id,
        input=ProjectInput(
            topic=preset.suggested_topic,
            tone=preset.suggested_tone,
            duration_seconds=preset.suggested_duration,
            target_platforms=[Platform(p) for p in preset.target_platforms],
            video_provider=preset.video_provider,
            model_tier=preset.model_tier,
            visual_preferences={"policy_pack": preset.policy_pack_id, "style": preset.suggested_style}
        )
    )

    # Project manually configured with matching options
    proj_manual = Project(
        id=fixed_id,
        input=ProjectInput(
            topic="Quantum Computing Breakthroughs in 2026",
            tone="authoritative tech documentary",
            duration_seconds=30,
            target_platforms=[Platform.YOUTUBE_SHORTS, Platform.TIKTOK, Platform.INSTAGRAM_REELS],
            video_provider="runway",
            model_tier="flagship",
            visual_preferences={"policy_pack": "general_audience", "style": "sleek corporate cyberpunk 3D motion graphics with glowing circuitry"}
        )
    )

    # Field-by-field deep diff
    diff = {}
    preset_dict = {
        "topic": proj_preset.input.topic,
        "tone": proj_preset.input.tone,
        "duration_seconds": proj_preset.input.duration_seconds,
        "target_platforms": [p.value for p in proj_preset.input.target_platforms],
        "video_provider": proj_preset.input.video_provider,
        "model_tier": proj_preset.input.model_tier,
        "visual_preferences": proj_preset.input.visual_preferences,
    }
    manual_dict = {
        "topic": proj_manual.input.topic,
        "tone": proj_manual.input.tone,
        "duration_seconds": proj_manual.input.duration_seconds,
        "target_platforms": [p.value for p in proj_manual.input.target_platforms],
        "video_provider": proj_manual.input.video_provider,
        "model_tier": proj_manual.input.model_tier,
        "visual_preferences": proj_manual.input.visual_preferences,
    }

    for k in preset_dict:
        if preset_dict[k] != manual_dict.get(k):
            diff[k] = {"preset": preset_dict[k], "manual": manual_dict.get(k)}

    # Assert diff is completely empty
    assert diff == {}, f"Unexpected domain diff between preset and manual project: {diff}"


def test_all_three_system_presets_create_working_projects_via_api():
    """Verify all 3 system presets produce working projects end-to-end through the API."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    presets = studio_preset_service.get_system_presets()
    assert len(presets) == 3

    for p in presets:
        payload = {
            "topic": p.suggested_topic,
            "tone": p.suggested_tone,
            "duration_seconds": p.suggested_duration,
            "target_platforms": p.target_platforms,
            "video_provider": p.video_provider,
            "model_tier": p.model_tier,
            "visual_preferences": {"policy_pack": p.policy_pack_id, "style": p.suggested_style or ""}
        }
        res = client.post("/api/projects", json=payload)
        assert res.status_code == 200, f"Failed to create project for preset {p.id}: {res.text}"
        data = res.json()
        proj_id = data["id"]
        assert data["video_provider"] == p.video_provider
        assert data["target_platforms"] == p.target_platforms

        # Generate prompts/scenes to confirm project is fully operational
        gen_res = client.post(f"/api/projects/{proj_id}/generate")
        assert gen_res.status_code == 200, f"Failed to generate prompts for preset {p.id}: {gen_res.text}"
        prompts = gen_res.json()
        assert len(prompts) > 0, f"No prompts generated for preset {p.id}"

