from typing import Final

TITLE_MAX_LENGTH: Final[int] = 100
TITLE_RECOMMENDED_MAX: Final[int] = 70
DESCRIPTION_MAX_LENGTH: Final[int] = 5000
HASHTAG_MAX_COUNT: Final[int] = 15
HASHTAG_MAX_LENGTH: Final[int] = 30
PINNED_COMMENT_MAX_LENGTH: Final[int] = 500
REQUIRED_DISCLOSURE: Final[str] = ""

RESTRICTED_WORDS: Final[tuple[str, ...]] = (
    "guaranteed results",
    "miracle cure",
    "get rich quick",
)
