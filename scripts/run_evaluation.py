import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.evaluation_service import EvaluationService  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Shorts prompt quality across a topic dataset.")
    parser.add_argument("--dataset", default=str(ROOT / "backend" / "evaluation" / "topics.json"))
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()

    cases = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    report = EvaluationService().evaluate(cases)
    rendered = json.dumps(report, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()

