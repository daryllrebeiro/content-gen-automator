from typing import Any, Protocol


class LLMProvider(Protocol):
    name: str

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        ...

