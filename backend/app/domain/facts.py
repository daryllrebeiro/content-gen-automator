from dataclasses import dataclass, field
from enum import Enum


class FactStatus(str, Enum):
    VERIFIED = "verified"
    SOURCE_PROVIDED = "source_provided"
    PARTIALLY_VERIFIED = "partially_verified"
    UNCERTAIN = "uncertain"
    CONTRADICTED = "contradicted"
    UNVERIFIED = "unverified"


@dataclass
class FactClaim:
    id: str
    text: str
    status: FactStatus = FactStatus.UNVERIFIED
    confidence: float = 0.0
    sources: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def approved_for_narration(self) -> bool:
        return self.status == FactStatus.VERIFIED

