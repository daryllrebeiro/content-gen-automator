from statistics import mean
from typing import Any

from app.domain.project import ProjectInput
from app.services.project_service import InMemoryProjectRepository, ProjectService


class EvaluationService:
    def evaluate(self, cases: list[dict[str, Any]]) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for case in cases:
            service = ProjectService(InMemoryProjectRepository())
            project = service.create(
                ProjectInput(
                    topic=case["topic"],
                    facts=case.get("facts", []),
                    duration_seconds=case.get("duration_seconds", 30),
                )
            )
            prompts = []
            try:
                for scene in project.scenes:
                    prompts.append(service.generate_next(project.id))
                    service.decide_prompt(project.id, scene.number, decision="approved", actor="evaluation", comment="Automated contract evaluation")
                scores = [prompt.quality_scores for prompt in prompts]
                average_scores = {
                    key: round(mean(score[key] for score in scores), 2)
                    for key in scores[0]
                }
                passed = average_scores["overall"] >= 0.9 and average_scores["safety"] == 1.0 and average_scores["timing"] == 1.0
                results.append({"topic": case["topic"], "passed": passed, "average_scores": average_scores, "scene_count": len(prompts)})
            except Exception as exc:
                results.append({"topic": case["topic"], "passed": False, "error": str(exc), "scene_count": len(prompts)})

        score_rows = [result["average_scores"] for result in results if "average_scores" in result]
        overall_scores = {
            key: round(mean(row[key] for row in score_rows), 2)
            for key in score_rows[0]
        } if score_rows else {}
        return {
            "total_cases": len(cases),
            "passed_cases": sum(1 for result in results if result["passed"]),
            "failed_cases": sum(1 for result in results if not result["passed"]),
            "overall_scores": overall_scores,
            "results": results,
        }
