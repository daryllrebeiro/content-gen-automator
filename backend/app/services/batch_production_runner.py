"""
Batch / Event-Driven Production Runner.
Processes unrendered approved projects in the background without human intervention.
Suitable for execution as a Cloud Run Job, cron task, or Pub/Sub event consumer.
"""

import time
from typing import Dict, List, Any
from app.services.project_service import ProjectService
from app.services.production_service import ProductionService
from app.adapters.grafana_telemetry import telemetry
from app.adapters.clickhouse_analytics import clickhouse_analytics

class BatchProductionRunner:
    def __init__(self, project_service: ProjectService = None, production_service: ProductionService = None):
        self.project_service = project_service or ProjectService()
        self.production_service = production_service or ProductionService()
        self.max_batch_size = 10

    def process_backlog(self, studio_id: str = "studio_default") -> Dict[str, Any]:
        """
        Scans repository for approved projects and automatically executes rendering and clip production.
        """
        repo = self.project_service.repository
        all_projects = list(getattr(repo, "projects", {}).values()) if hasattr(repo, "projects") else []
        
        candidates = [
            p for p in all_projects 
            if p.status in {p.status.APPROVED, p.status.COMPLETED, p.status.VIDEO_APPROVED}
        ]

        processed_jobs = []
        errors = []

        for project in candidates[:self.max_batch_size]:
            p_id = str(project.id)
            # Verify cost ceiling before batch execution
            budget = getattr(project.input, "token_budget", 50000)
            exceeded, consumed, limit = telemetry.is_cost_ceiling_exceeded(p_id, budget)
            if exceeded:
                errors.append(f"Project {p_id} skipped: Token ceiling ({consumed}/{limit}) exceeded.")
                continue

            try:
                for scene in project.scenes:
                    job = self.production_service.submit_clip(project, scene.number, repo)
                    processed_jobs.append({"project_id": p_id, "scene_number": scene.number, "job_id": job.job_id})
                    clickhouse_analytics.log_event("batch_clip_rendered", p_id, {"scene": scene.number, "job_id": job.job_id})
            except Exception as e:
                errors.append(f"Project {p_id} error: {str(e)}")

        return {
            "status": "completed",
            "batch_processed_count": len(processed_jobs),
            "jobs": processed_jobs,
            "errors": errors,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }


batch_production_runner = BatchProductionRunner()
