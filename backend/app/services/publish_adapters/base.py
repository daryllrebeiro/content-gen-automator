from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from app.domain.project import Project, Platform

@dataclass
class PublishResult:
    platform: Platform
    status: str  # "PUBLISHED" | "READY_FOR_MANUAL_UPLOAD" | "FAILED"
    asset_ref: str
    published_url: Optional[str] = None
    package_dir: Optional[str] = None
    manifest: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

class BasePublishAdapter:
    def publish(self, project: Project, asset_path: str) -> PublishResult:
        raise NotImplementedError
