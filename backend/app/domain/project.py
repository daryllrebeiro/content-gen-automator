from enum import Enum
from typing import Literal


DurationSeconds = Literal[10, 20, 30]


class ProjectStatus(str, Enum):
    CREATED = "CREATED"
    INPUT_RECEIVED = "INPUT_RECEIVED"
    FACT_CHECKING = "FACT_CHECKING"
    STORY_CREATED = "STORY_CREATED"
    SCENES_PLANNED = "SCENES_PLANNED"
    AWAITING_NEXT = "AWAITING_NEXT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def scene_count(duration_seconds: DurationSeconds) -> int:
    return duration_seconds // 10

