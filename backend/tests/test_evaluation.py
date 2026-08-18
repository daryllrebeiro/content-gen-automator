from app.services.evaluation_service import EvaluationService


def test_evaluation_service_reports_all_cases():
    report = EvaluationService().evaluate(
        [
            {"topic": "A short evaluation topic", "duration_seconds": 10},
            {"topic": "Another short evaluation topic", "duration_seconds": 20},
        ]
    )
    assert report["total_cases"] == 2
    assert report["passed_cases"] == 2
    assert report["overall_scores"]["overall"] > 0.9
