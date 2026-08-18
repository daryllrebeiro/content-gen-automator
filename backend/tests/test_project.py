import pytest

from app.domain.project import scene_count


@pytest.mark.parametrize(
    ("duration_seconds", "expected"),
    [(10, 1), (20, 2), (30, 3)],
)
def test_scene_count(duration_seconds, expected):
    assert scene_count(duration_seconds) == expected

