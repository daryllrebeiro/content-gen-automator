from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Callable


class ProviderFailure(RuntimeError):
    def __init__(self, message: str, *, retryable: bool, attempts: int = 1) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.attempts = attempts


def is_retryable_provider_error(error: Exception) -> bool:
    message = str(error).lower()
    return isinstance(error, (TimeoutError, ConnectionError, OSError)) or any(
        marker in message for marker in ("timeout", "temporarily unavailable", "rate limit", "429", "500", "502", "503", "504")
    )


class RetryingProvider:
    """Bounded retry adapter. Model output remains untrusted until pipeline validation."""

    def __init__(self, provider: Any, *, max_attempts: int = 3, backoff_seconds: float = 0.05, timeout_seconds: float = 30.0) -> None:
        self.provider = provider
        self.name = provider.name
        self.model = getattr(provider, "model", provider.name)
        self.max_attempts = max(1, max_attempts)
        self.backoff_seconds = max(0.0, backoff_seconds)
        self.timeout_seconds = max(0.1, timeout_seconds)

    def generate_json(self, *, system_prompt: str, user_prompt: str, response_schema: dict[str, Any]) -> dict[str, Any]:
        return self._call(lambda: self.provider.generate_json(system_prompt=system_prompt, user_prompt=user_prompt, response_schema=response_schema))

    def verify_claim(self, claim, source_urls):
        return self._call(lambda: self.provider.verify_claim(claim, source_urls))

    def _call(self, operation: Callable[[], Any]) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                executor = ThreadPoolExecutor(max_workers=1)
                future = executor.submit(operation)
                try:
                    return future.result(timeout=self.timeout_seconds)
                except FutureTimeoutError as error:
                    future.cancel()
                    raise TimeoutError(f"Provider operation exceeded {self.timeout_seconds:g} seconds.") from error
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
            except Exception as error:  # provider SDKs expose different exception types
                last_error = error
                if not is_retryable_provider_error(error) or attempt == self.max_attempts:
                    raise ProviderFailure(str(error), retryable=is_retryable_provider_error(error), attempts=attempt) from error
                time.sleep(self.backoff_seconds * attempt)
        raise ProviderFailure(str(last_error), retryable=True, attempts=self.max_attempts)
