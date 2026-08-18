from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.domain.integration import DeliveryJob, ExportManifest
from app.domain.project import Project


class DeliveryService:
    def create_manifest(self, project: Project, repository, export_service, *, ttl_seconds: int = 3600) -> ExportManifest:
        data = export_service.export_json(project)
        markdown = export_service.render_markdown(project)
        canonical = json.dumps({"markdown": markdown, "data": data}, sort_keys=True, separators=(",", ":"), default=str)
        checksum = hashlib.sha256(canonical.encode()).hexdigest()
        manifest = ExportManifest(str(uuid4()), str(project.id), "export_v1", checksum, markdown, data, datetime.now(timezone.utc), datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds))
        if hasattr(repository, "save_export_manifest"):
            repository.save_export_manifest(manifest)
        return manifest

    def sign_manifest(self, manifest: ExportManifest, secret: str) -> str:
        payload = f"{manifest.manifest_id}:{int(manifest.expires_at.timestamp())}"
        signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
        return f"{encoded}.{signature}"

    def verify_token(self, token: str, secret: str) -> str | None:
        try:
            encoded, signature = token.split(".", 1)
            payload = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode()
            expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return None
            manifest_id, expires = payload.split(":", 1)
            if datetime.now(timezone.utc).timestamp() > int(expires):
                return None
            return manifest_id
        except (ValueError, TypeError):
            return None

    def queue_delivery(self, project: Project, manifest: ExportManifest, repository) -> DeliveryJob:
        job = DeliveryJob(str(uuid4()), str(project.id), manifest.manifest_id, "QUEUED")
        if hasattr(repository, "save_delivery_job"):
            repository.save_delivery_job(job)
        return job
