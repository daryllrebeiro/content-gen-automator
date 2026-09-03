from uuid import uuid4
from app.services.batch_production_runner import BatchProductionRunner
from app.adapters.youtube_analytics import youtube_analytics
from app.services.project_service import ProjectService
from app.domain.project import ProjectInput

def test_batch_production_runner_execution():
    svc = ProjectService()
    runner = BatchProductionRunner(project_service=svc)
    project = svc.create(
        ProjectInput(topic="Bioluminescent Depths", duration_seconds=10)
    )
    res = runner.process_backlog()
    assert res["status"] == "completed"
    assert "timestamp" in res


def test_youtube_analytics_feedback_loop():
    p_id = str(uuid4())
    # Ingest video performance
    ingested = youtube_analytics.ingest_video_performance(
        video_id="yt-test-123",
        project_id=p_id,
        views=25000,
        likes=1840,
        retention_rate=0.88,
        hook_style="curious_cinematic"
    )
    assert ingested["views"] == 25000
    assert ingested["retention_rate"] == 0.88

    # Fetch Director's Post-Mortem
    post_mortem = youtube_analytics.get_directors_post_mortem(p_id)
    assert post_mortem["total_views"] == 25000
    assert post_mortem["retention_verdict"] == "HIGH_RETENTION"
    assert len(post_mortem["insights"]) > 0
