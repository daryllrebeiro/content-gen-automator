import pytest

from app.domain.project import ProjectInput, ProjectStatus, scene_count
from app.services.project_service import InMemoryProjectRepository, ProjectService, ProjectStateError


@pytest.mark.parametrize(
    ("duration_seconds", "expected"),
    [(10, 1), (20, 2), (30, 3)],
)
def test_scene_count(duration_seconds, expected):
    assert scene_count(duration_seconds) == expected


def test_project_generates_prompts_one_at_a_time():
    service = ProjectService(InMemoryProjectRepository())
    project = service.create(ProjectInput(topic="A small idea becomes global", duration_seconds=30))

    first = service.generate_next(project.id)
    assert first.scene_number == 1
    assert project.status == ProjectStatus.AWAITING_NEXT
    assert "exactly 10 seconds" in first.text
    assert first.estimated_narration_seconds < 9

    second = service.generate_next(project.id)
    third = service.generate_next(project.id)
    assert (second.scene_number, third.scene_number) == (2, 3)
    assert project.status == ProjectStatus.COMPLETED


def test_next_prompt_is_idempotent_and_cannot_exceed_scene_count():
    service = ProjectService(InMemoryProjectRepository())
    project = service.create(ProjectInput(topic="A ten second story", duration_seconds=10))

    first = service.generate_next(project.id)
    retry = service.generate_next(project.id)
    assert retry is first

    try:
        service.generate_next(project.id)
    except ProjectStateError:
        pass
    else:
        raise AssertionError("Expected generation beyond the project scene count to fail")
