from typing import Final


ALLOWED_DURATIONS: Final[tuple[int, ...]] = (10, 20, 30)
CLIP_DURATION_SECONDS: Final[int] = 10
NARRATION_CUTOFF_SECONDS: Final[float] = 9.0
MAX_NARRATION_WORDS: Final[int] = 20
PROMPT_TEMPLATE_VERSION: Final[str] = "prompt_composer_v1"
SAFETY_POLICY_VERSION: Final[str] = "global_video_policy_v1"
VOICE_LOCK_ID: Final[str] = "documentary_voice_01"

REQUIRED_PROMPT_SECTIONS: Final[tuple[str, ...]] = (
    "FORMAT",
    "CONTINUITY LOCK",
    "SCENE / VISUAL STORY",
    "CAMERA AND COMPOSITION",
    "NARRATION — EXACT SCRIPT",
    "CAPTIONS",
    "AUDIO",
    "SAFETY AND EXCLUSIONS",
    "FINAL GENERATION REQUIREMENTS",
)


def scene_count_for_duration(duration_seconds: int) -> int:
    if duration_seconds not in ALLOWED_DURATIONS:
        raise ValueError("Duration must be 10, 20, or 30 seconds.")
    return duration_seconds // CLIP_DURATION_SECONDS

