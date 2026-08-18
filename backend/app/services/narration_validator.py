from app.domain.generation import NarrationDraft


MAX_NARRATION_SECONDS = 9.0
MAX_NARRATION_WORDS = 20


class NarrationValidationError(ValueError):
    pass


def draft_narration(text: str) -> NarrationDraft:
    normalized = " ".join(text.split()).strip()
    if not normalized:
        raise NarrationValidationError("Narration cannot be empty.")

    word_count = len(normalized.split())
    estimated_seconds = round(word_count / 140 * 60, 1)
    draft = NarrationDraft(normalized, word_count, estimated_seconds)
    validate_narration(draft)
    return draft


def validate_narration(draft: NarrationDraft) -> None:
    if draft.word_count > MAX_NARRATION_WORDS:
        raise NarrationValidationError(
            f"Narration contains {draft.word_count} words; maximum is {MAX_NARRATION_WORDS}."
        )
    if draft.estimated_seconds >= MAX_NARRATION_SECONDS:
        raise NarrationValidationError("Narration must finish before the 9-second cutoff.")
    if draft.text[-1] not in ".!?\"”':;)":
        raise NarrationValidationError("Narration must end as a complete sentence.")

