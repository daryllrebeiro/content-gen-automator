import re
import sys
from pathlib import Path
from uuid import UUID
from starlette.testclient import TestClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import app
from app.config import settings

TEST_INTEGRATION_TOKEN = "test-integration-service-token-secret"
if not settings.integration_service_token:
    object.__setattr__(settings, "integration_service_token", TEST_INTEGRATION_TOKEN)

# Mirror frontend SDK behavior (like frontend/lib/api.ts):
# Keep track of project owner tokens,
# and automatically inject X-Project-Owner-Token for /api/projects/{project_id}/*
# and Authorization: Bearer for /api/integrations/*
# unless the caller explicitly supplied headers (or passed empty token / Skip-Auto-Owner-Token).

_test_project_tokens: dict[str, str] = {}
_original_request = TestClient.request

def _auto_token_request(self, method, url, *args, **kwargs):
    headers = dict(kwargs.get("headers") or {})
    url_str = str(url)

    # Automatic integration token injection for integration and admin endpoints
    if any(prefix in url_str for prefix in ("/api/integrations", "/api/governance/policy-packs", "/api/presets", "/metrics")):
        if "Authorization" not in headers and not headers.get("Skip-Auto-Integration-Token"):
            headers["Authorization"] = f"Bearer {settings.integration_service_token}"
            kwargs["headers"] = headers

    if "Skip-Auto-Integration-Token" in headers:
        del headers["Skip-Auto-Integration-Token"]
        kwargs["headers"] = headers

    m = re.search(r"/api/(?:projects|telemetry/budget-status|exports)/([0-9a-fA-F-]+)", url_str)
    if m:
        p_id = m.group(1)
        if "X-Project-Owner-Token" not in headers and not headers.get("Skip-Auto-Owner-Token"):
            stored = _test_project_tokens.get(p_id)
            if not stored:
                from app.services.project_service import ProjectService
                try:
                    p = ProjectService().repository.get(UUID(p_id))
                    stored = getattr(p, "owner_token", None)
                    if stored:
                        _test_project_tokens[p_id] = stored
                except Exception:
                    pass
            if stored:
                headers["X-Project-Owner-Token"] = stored
                kwargs["headers"] = headers

    if "Skip-Auto-Owner-Token" in headers:
        del headers["Skip-Auto-Owner-Token"]
        kwargs["headers"] = headers

    response = _original_request(self, method, url, *args, **kwargs)

    if method.upper() == "POST" and "/projects" in url_str and response.status_code in (200, 201):
        try:
            body = response.json()
            if isinstance(body, dict):
                p_id = str(body.get("id") or body.get("project_id") or "")
                token = body.get("owner_token")
                if p_id and not token:
                    from app.services.project_service import ProjectService
                    try:
                        p = ProjectService().repository.get(UUID(p_id))
                        token = getattr(p, "owner_token", None)
                    except Exception:
                        pass
                if p_id and token:
                    _test_project_tokens[p_id] = token
        except Exception:
            pass

    return response

TestClient.request = _auto_token_request

import pytest

@pytest.fixture(autouse=True)
def reset_rate_limiters():
    from app.api.routes import project_creation_limiter
    project_creation_limiter.requests.clear()
    yield

