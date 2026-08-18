from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class IdempotencyRecord:
    key: str
    operation: str
    request_hash: str
    response: dict[str, Any]
    created_at: datetime


@dataclass
class AuditEvent:
    event_id: str
    event_type: str
    project_id: str | None
    request_id: str | None
    metadata: dict[str, Any]
    created_at: datetime

    @classmethod
    def now(cls, event_id: str, event_type: str, project_id: str | None = None, request_id: str | None = None, metadata: dict[str, Any] | None = None) -> "AuditEvent":
        return cls(event_id, event_type, project_id, request_id, metadata or {}, datetime.now(timezone.utc))

