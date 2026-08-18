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

The Gemini provider is available behind the provider abstraction. The mock provider remains the default for local development and tests.

To enable the Gemini adapter after installing dependencies, set:

```text
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-2.5-flash
```

The default remains `mock`, so local development and tests do not require an API key.

Provider hardening controls are available for deployed Gemini usage:

```text
PROVIDER_MAX_ATTEMPTS=3
PROVIDER_TIMEOUT_SECONDS=30
```

Transient provider failures are retried within these bounds. Permanent failures and unrepaired structured output fail closed before project or prompt persistence.

## n8n integration foundation

Phase 1 exposes an integration-safe project creation endpoint:

```text
POST /api/integrations/projects
Idempotency-Key: <stable-workflow-key>
X-Request-ID: <optional-correlation-id>
Authorization: Bearer <INTEGRATION_SERVICE_TOKEN>
```

The endpoint returns a stable `project_id` on retries. Reusing a key with a different payload returns `409`. In development, authentication is open when `INTEGRATION_SERVICE_TOKEN` is empty; set the token in staging and production. Reliability records are persisted in PostgreSQL by migration `database/migrations/002_reliability.sql`.

Apply migrations in a deployed environment with:

```powershell
$env:DATABASE_URL = "postgresql://..."
python scripts/migrate.py
```

The integration surface requires human approval before the next scene is generated. Use the `approve` or `reject` prompt endpoints with an actor, comment, and idempotency key; decisions are retained in `approval_events`.

## End-to-end smoke test

With the backend dependencies installed, run from the repository root:

```powershell
$env:PYTHONPATH = "backend"
python scripts/smoke_test.py
```

The smoke test exercises readiness, project creation, all three prompts, scoped regeneration, and export. To exercise Gemini, set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY` first.
