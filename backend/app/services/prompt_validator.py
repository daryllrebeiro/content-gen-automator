from app.domain.generation import ProductionContract
from app.domain.project import VideoPrompt
from app.policies.contract import REQUIRED_PROMPT_SECTIONS


class PromptValidationError(ValueError):
    pass


def validate_prompt(prompt: VideoPrompt, contract: ProductionContract) -> None:
    required_fragments = ("9:16 vertical", "exactly 10 seconds", "final second", *REQUIRED_PROMPT_SECTIONS)
    missing = [fragment for fragment in required_fragments if fragment not in prompt.text]
    if missing:
        raise PromptValidationError(f"Prompt is missing required sections: {', '.join(missing)}")
    if prompt.total_scenes < 1 or prompt.total_scenes > 3:
        raise PromptValidationError("A project may contain between one and three scenes.")
    if prompt.narration_word_count > 20:
        raise PromptValidationError("Prompt narration exceeds the safe word limit.")
    if prompt.estimated_narration_seconds >= contract.narration_max_seconds:
        raise PromptValidationError("Prompt narration reaches the audio cutoff.")
