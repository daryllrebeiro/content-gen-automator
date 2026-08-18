import pytest

from app.providers.reliability import ProviderFailure, RetryingProvider
from app.services.prompt_pipeline import StructuredOutputError, _generate_structured


class FlakyProvider:
    name = "flaky"
    model = "flaky-v1"

    def __init__(self):
        self.calls = 0

    def generate_json(self, **kwargs):
        self.calls += 1
        if self.calls < 3:
            raise TimeoutError("provider timeout")
        return {"text": "Valid output."}


class BrokenProvider:
    name = "broken"

    def generate_json(self, **kwargs):
        raise RuntimeError("invalid API key")


def test_retrying_provider_retries_transient_failures_with_a_bound():
    provider = FlakyProvider()
    result = RetryingProvider(provider, max_attempts=3, backoff_seconds=0).generate_json(system_prompt="", user_prompt="", response_schema={})

    assert result["text"] == "Valid output."
    assert provider.calls == 3


def test_retrying_provider_enforces_timeout():
    import time

    class SlowProvider:
        name = "slow"
        def generate_json(self, **kwargs):
            time.sleep(0.15)
            return {"text": "Too late."}

    with pytest.raises(ProviderFailure) as error:
        RetryingProvider(SlowProvider(), max_attempts=1, timeout_seconds=0.1).generate_json(system_prompt="", user_prompt="", response_schema={})

    assert error.value.retryable is True


def test_retrying_provider_classifies_permanent_failures():
    with pytest.raises(ProviderFailure) as error:
        RetryingProvider(BrokenProvider(), max_attempts=3, backoff_seconds=0).generate_json(system_prompt="", user_prompt="", response_schema={})

    assert error.value.retryable is False
    assert error.value.attempts == 1


def test_structured_output_repair_is_bounded():
    class RepairProvider:
        name = "repair"
        def __init__(self):
            self.calls = 0
        def generate_json(self, **kwargs):
            self.calls += 1
            return {} if self.calls == 1 else {"text": "Repaired output."}

    provider = RepairProvider()
    result, repairs = _generate_structured(provider, system_prompt="", user_prompt="original", response_schema={}, required=("text",), max_repairs=1)

    assert result["text"] == "Repaired output."
    assert repairs == 1
    assert provider.calls == 2


def test_structured_output_does_not_retry_forever():
    class AlwaysBroken:
        name = "broken"
        def generate_json(self, **kwargs):
            return {}

    with pytest.raises(StructuredOutputError):
        _generate_structured(AlwaysBroken(), system_prompt="", user_prompt="", response_schema={}, required=("text",), max_repairs=1)
