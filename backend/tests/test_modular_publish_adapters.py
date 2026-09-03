import os
import json
from uuid import uuid4
from app.domain.project import Project, ProjectInput, Platform
from app.services.publish_adapters import (
    get_publish_adapter,
    YouTubePublishAdapter,
    TikTokPublishAdapter,
    InstagramPublishAdapter
)

def test_get_publish_adapter_factory():
    yt = get_publish_adapter(Platform.YOUTUBE_SHORTS)
    assert isinstance(yt, YouTubePublishAdapter)

    tt = get_publish_adapter(Platform.TIKTOK)
    assert isinstance(tt, TikTokPublishAdapter)

    ig = get_publish_adapter(Platform.INSTAGRAM_REELS)
    assert isinstance(ig, InstagramPublishAdapter)

def test_youtube_publish_adapter():
    inp = ProjectInput(topic="Bioluminescence")
    proj = Project(id=uuid4(), input=inp)
    adapter = YouTubePublishAdapter()
    res = adapter.publish(proj, "app/static/output/dummy.mp4")
    assert res.platform == Platform.YOUTUBE_SHORTS
    assert res.status == "PUBLISHED"
    assert "youtube.com/shorts" in res.published_url

def test_tiktok_publish_adapter_manual_packaging(monkeypatch):
    monkeypatch.delenv("TIKTOK_ACCESS_TOKEN", raising=False)
    inp = ProjectInput(topic="Underwater Geysers")
    proj = Project(id=uuid4(), input=inp)
    proj.story_hook = "Did you know boiling water erupts miles beneath the Pacific?"

    adapter = TikTokPublishAdapter()
    res = adapter.publish(proj, "app/static/output/dummy_tiktok.mp4")

    assert res.platform == Platform.TIKTOK
    assert res.status == "READY_FOR_MANUAL_UPLOAD"
    assert res.package_dir is not None
    assert os.path.exists(f"{res.package_dir}/captions.vtt")
    assert os.path.exists(f"{res.package_dir}/post_copy.txt")
    assert os.path.exists(f"{res.package_dir}/manifest.json")

    with open(f"{res.package_dir}/manifest.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["platform"] == "TIKTOK"
        assert "#TikTokShorts" in data["hashtags"]

def test_instagram_publish_adapter_manual_packaging(monkeypatch):
    monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)
    inp = ProjectInput(topic="Supermassive Black Holes")
    proj = Project(id=uuid4(), input=inp)
    proj.story_hook = "Nothing escapes their gravitational pull."

    adapter = InstagramPublishAdapter()
    res = adapter.publish(proj, "app/static/output/dummy_reels.mp4")

    assert res.platform == Platform.INSTAGRAM_REELS
    assert res.status == "READY_FOR_MANUAL_UPLOAD"
    assert res.package_dir is not None
    assert os.path.exists(f"{res.package_dir}/captions.vtt")
    assert os.path.exists(f"{res.package_dir}/post_copy.txt")
    assert os.path.exists(f"{res.package_dir}/manifest.json")

    with open(f"{res.package_dir}/manifest.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["platform"] == "INSTAGRAM_REELS"
        assert "#Reels" in data["hashtags"]
