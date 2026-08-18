# Animated YouTube Shorts Prompt Agent

Stateful AI orchestration for creating consistent, animated YouTube Shorts prompts.

The MVP accepts a video idea and creates one to three connected prompts. Each prompt represents one ten-second, 9:16 animated clip. The system preserves a shared story, visual style, characters, narration voice, safety policy, and production contract across every scene.

## Current status

The repository is scaffolded for the foundation milestone. The backend currently exposes a health endpoint and the domain layer contains the first duration and project-state rules.

See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for the complete product and engineering plan.

## Planned stack

- Frontend: Next.js, React, TypeScript
- Backend: Python, FastAPI, Pydantic
- Persistence: PostgreSQL
- Initial provider: deterministic mock provider for local development and tests

## Local setup

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/health`.

The real LLM provider will be added after the state machine and validation contracts are covered by tests.

