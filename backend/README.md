# Backend

FastAPI service for project state, fact validation, story planning, continuity management, prompt generation, and export.

Run locally from this directory:

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run the prompt evaluation dataset from the repository root:

```powershell
$py = "C:\path\to\python.exe"
& $py scripts/run_evaluation.py --output evaluation-report.json
```

The evaluator uses the mock provider by default, making it suitable for prompt-template regression tests without API costs.
