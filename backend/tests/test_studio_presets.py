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

def test_preset_instantiates_identical_project_configuration():
    # Retrieve preset
    preset = studio_preset_service.get_preset("multi_platform_viral")
    assert preset is not None

    # Instantiate from preset
    proj_from_preset = ProjectInput(
        topic=preset.suggested_topic or "Test",
        target_platforms=[Platform(p) for p in preset.target_platforms],
        video_provider=preset.video_provider,
        model_tier=preset.model_tier,
        visual_preferences={"policy_pack": preset.policy_pack_id, "style": preset.suggested_style}
    )

    # Manually configure identical project
    proj_manual = ProjectInput(
        topic="Quantum Computing Breakthroughs in 2026",
        target_platforms=[Platform.YOUTUBE_SHORTS, Platform.TIKTOK, Platform.INSTAGRAM_REELS],
        video_provider="runway",
        model_tier="flagship",
        visual_preferences={"policy_pack": "general_audience", "style": "sleek corporate cyberpunk 3D motion graphics with glowing circuitry"}
    )

    assert proj_from_preset.target_platforms == proj_manual.target_platforms
    assert proj_from_preset.video_provider == proj_manual.video_provider
    assert proj_from_preset.model_tier == proj_manual.model_tier
    assert proj_from_preset.visual_preferences["policy_pack"] == proj_manual.visual_preferences["policy_pack"]
