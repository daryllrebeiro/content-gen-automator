from typing import Protocol

from app.domain.facts import FactClaim


class FactChecker(Protocol):
    def verify_claim(self, claim: FactClaim, source_urls: list[str]) -> FactClaim:
        ...

