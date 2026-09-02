from typing import Dict, Any, List
from uuid import UUID
from app.services.project_service import ProjectService
from app.services.publishing_gate_service import PublishingGateService

project_service = ProjectService()
gate_service = PublishingGateService()

def check_publishing_gates_tool(project_id: str) -> Dict[str, Any]:
    """
    Executes all 7 fail-closed publishing gates against a project to ensure 100% readiness for YouTube release.
    
    Args:
        project_id: UUID string of the project.
    """
    project = project_service.repository.get(UUID(project_id))
    report = gate_service.check(project, project_service.repository)
    return {
        "can_publish": report.can_publish,
        "failed_gates": report.failed_gates,
        "gate_count_passed": 7 - len(report.failed_gates)
    }
