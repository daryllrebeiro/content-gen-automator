from fastapi import FastAPI, Response, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import os
import hmac
import json
from uuid import UUID
from typing import Dict, Any, List

from app.api.byok import ByokCredentials, get_byok_credentials
from app.api.integration_auth import require_integration_auth

from app.api.routes import router
from app.config import settings
from app.adapters.grafana_telemetry import telemetry
from app.adapters.parallel_search import parallel_search
from app.adapters.clickhouse_analytics import clickhouse_analytics
from app.adapters.ibm_governance import ibm_governance
from app.services.policy_pack_service import policy_pack_service, GovernancePolicyPack
from app.services.compliance_certificate_service import compliance_certificate_service
from app.services.localization_service import localization_service
from app.services.brand_kit_service import brand_kit_service

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api.project_auth import require_project_owner, project_service

is_prod = settings.app_env.lower() == "production"

app = FastAPI(
    title="Agentic Cinema: ContentGenAutomator Studio Core",
    version="0.3.0",
    description="Stateful multi-agent orchestration for cinematic video generation, powered by Gemini Enterprise ADK and 5-partner ecosystem.",
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Idempotency-Key",
        "X-Request-ID",
        "X-API-Key",
        "X-Project-Owner-Token",
        "X-Expected-Version",
        "X-Gemini-API-Key",
        "X-Runway-API-Key",
        "X-Kling-API-Key",
        "X-ElevenLabs-API-Key",
    ],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = exc.errors()
    sanitized_errors = []
    for err in errors:
        err_copy = dict(err)
        val = err_copy.get("input")
        if isinstance(val, str) and len(val) > 100:
            err_copy["input"] = val[:100] + f"... [truncated {len(val)-100} chars]"
        elif isinstance(val, dict):
            sanitized_dict = {}
            for k, v in val.items():
                if isinstance(v, str) and len(v) > 100:
                    sanitized_dict[k] = v[:100] + f"... [truncated {len(v)-100} chars]"
                else:
                    sanitized_dict[k] = v
            err_copy["input"] = sanitized_dict
        sanitized_errors.append(err_copy)
    return JSONResponse(status_code=422, content={"detail": sanitized_errors})

app.include_router(router)

# ── 1. Observability (Grafana Labs) ──────────────────────────────────────────

@app.get("/metrics", tags=["observability"], dependencies=[Depends(require_integration_auth)])
def get_prometheus_metrics():
    """Prometheus exposition format for Grafana Cloud scraper."""
    content = telemetry.generate_prometheus_metrics()
    return Response(content=content, media_type="text/plain; version=0.0.4")


# ── 2. 5-Partner Ecosystem Status ────────────────────────────────────────────

@app.get("/api/partners/status", tags=["partners"])
def get_partner_ecosystem_status():
    """Returns the live runtime status of all 5 hackathon partner integrations."""
    return {
        "hackathon": "Agentic Cinema: The Blockbuster Hackathon",
        "primary_track": "IBM watsonx (Governance)",
        "google_cloud_gemini": {
            "model": os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            "framework": "Google Cloud Agent Development Kit (ADK)",
            "status": "ready"
        },
        "partners": {
            "grafana_labs": telemetry.get_summary(),
            "replit": {
                "partner": "Replit",
                "status": "ready",
                "config_present": os.path.exists("../.replit") or os.path.exists(".replit"),
                "deployment_target": "Cloud Run / Replit Agent"
            },
            "parallel": {
                "partner": "Parallel",
                "status": "active",
                "cached_topics": len(parallel_search._cache),
                "mode": "agent_dense_search"
            },
            "clickhouse": clickhouse_analytics.get_analytics_summary(),
            "ibm_watsonx": {
                "partner": "IBM watsonx.governance",
                "status": "guardrails_active",
                "policy_packs_loaded": len(policy_pack_service.list_policy_packs()),
                "policy_enforcement": "Brand Safety, Copyright Clearance & Factual Hallucination Cross-Referencing"
            }
        }
    }


# ── 3. IBM watsonx Governance & Compliance ────────────────────────────────────


@app.post("/api/governance/inline-check", tags=["governance"])
def inline_governance_check(payload: dict, request: Request):
    """Debounced live-edit advisory check for studio editors."""
    text = payload.get("text", "")
    raw_project_id = payload.get("project_id", "")
    policy_pack = payload.get("policy_pack", "general_audience")

    # OFF-07: Audit Poisoning Defense: Only attribute audit events to project_id if caller is verified owner
    effective_project_id = ""
    if raw_project_id:
        owner_token = request.headers.get("X-Project-Owner-Token")
        try:
            from uuid import UUID
            p_uuid = UUID(raw_project_id)
            proj = project_service.repository.get(p_uuid)
            if owner_token and getattr(proj, "owner_token", None) and hmac.compare_digest(owner_token, proj.owner_token):
                effective_project_id = str(raw_project_id)
        except Exception:
            effective_project_id = ""

    return ibm_governance.audit_prompt(text, project_id=effective_project_id, policy_pack=policy_pack)

# ── 4. Parallel Research & Grounding ──────────────────────────────────────────

@app.post("/api/research/parallel", tags=["research"])
def research_topic_with_parallel(payload: dict):
    topic = payload.get("topic", "")
    tone = payload.get("tone", "curious documentary")
    return parallel_search.research_topic(topic, tone)

@app.post("/api/research/recommend-topics", tags=["research"])
def recommend_trending_topics(payload: dict = None):
    category = payload.get("category", "science_nature") if payload else "science_nature"
    return parallel_search.recommend_topics(category)


# ── 5. ClickHouse Analytics & Command Center ─────────────────────────────────

@app.get("/api/analytics/clickhouse", tags=["analytics"])
def get_clickhouse_analytics():
    return clickhouse_analytics.get_analytics_summary()

@app.get("/api/analytics/command-center", tags=["analytics"])
def get_studio_command_center():
    return clickhouse_analytics.get_command_center_feed()

@app.get("/api/analytics/anomalies", tags=["analytics"])
def get_analytics_anomalies():
    return clickhouse_analytics.detect_anomalies()


# ── 6. Localization & Brand Kit ──────────────────────────────────────────────

@app.post(
    "/api/exports/{project_id}/locales/{locale}",
    tags=["localization"],
    dependencies=[Depends(require_project_owner)],
)
def localize_project_export(
    project_id: UUID,
    locale: str,
    payload: dict,
    byok: ByokCredentials = Depends(get_byok_credentials)
):
    from app.api.byok import resolve_gemini_key
    topic = payload.get("topic", "")
    narration_en = payload.get("narration_en", "")
    api_key = resolve_gemini_key(byok)
    return localization_service.localize_project(str(project_id), topic, narration_en, locale, api_key=api_key)

@app.get("/api/brand-kits/{studio_id}", tags=["brand_kit"])
def get_studio_brand_kit(studio_id: str = "studio_default"):
    return brand_kit_service.get_brand_kit(studio_id)

@app.get(
    "/api/projects/{project_id}/audit-log/export",
    tags=["audit"],
    dependencies=[Depends(require_project_owner)],
)
def export_soc2_audit_log(project_id: UUID):
    """Exports full SOC2-style event audit log for compliance inspection."""
    from datetime import datetime, timezone
    from app.services.project_service import ProjectNotFoundError
    try:
        project = project_service.repository.get(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc

    repo = project_service.repository
    raw_events = repo.get_audit_events(str(project_id)) if hasattr(repo, "get_audit_events") else []
    
    event_records = [
        {
            "event_id": e.event_id,
            "event": e.event_type.upper().replace(".", "_"),
            "timestamp": e.created_at.isoformat() if hasattr(e.created_at, "isoformat") else str(e.created_at),
            "metadata": e.metadata,
        }
        for e in raw_events
    ]
    return {
        "project_id": str(project_id),
        "topic": project.input.topic,
        "format": "SOC2_TYPE_II_COMPLIANT_EVENT_STREAM",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(event_records),
        "event_records": event_records,
    }


os.makedirs("app/static/audio", exist_ok=True)
os.makedirs("app/static/video", exist_ok=True)
os.makedirs("app/static/output", exist_ok=True)
os.makedirs("app/static/branding", exist_ok=True)
