# Animated YouTube Shorts Prompt Agent & Automation Engine

Stateful AI orchestration for creating consistent, animated YouTube Shorts, featuring full publishing validation, asset auditing, and YouTube publication gates.

## Project Architecture

```text
       Frontend (Next.js)          n8n (Orchestration)
              │                           │
              └──────────┬────────────────┘
                         ▼
                FastAPI Agent API
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   PostgreSQL      LLM Provider     Fact Engine
```

The system accepts a topic and optional fact inputs, plans a multi-scene storyboard, locks the visual style and voice profile (continuity locks), generates narration scripts and video-generation prompts, submits clips to rendering engines, audits the rendered assets, signs off on metadata, and publishes to YouTube.

---

## Current Status (Phase 8 Complete)

The system is fully developed through **Phase 8 (Publishing Automation)**:
1. **Interactive Frontend Workflow Dashboard:** A modern dark-mode dashboard handling prompt approval, asynchronous video render queuing, mock video rendering simulation, clip verification, publishing metadata sign-off, safety gate checks, and YouTube publishing status tracking.
2. **Robust Backend API:** Complete integration routes, idempotency checks, event-based auditing, fact checking, export delivery, production callbacks, and YouTube upload status machines.
3. **Fail-Closed Publishing Gate:** Enforces 7 safety and completeness checks in the API layer before video delivery is permitted.

---

## Local Setup & Development

### 1. Database Setup

Ensure PostgreSQL is running and set your database connection string in your environment:
```powershell
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/contentgen"
$env:PROJECT_REPOSITORY = "postgres" # or "memory" for in-memory DB
python scripts/migrate.py
```

### 2. Start the Backend API

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. You can inspect the interactive OpenAPI documentation at `http://127.0.0.1:8000/docs`.

### 3. Start the Frontend Dashboard

Ensure Node.js is installed. From the `frontend` directory:

```powershell
cd frontend
pnpm install # or npm install
npm run dev
```

Open `http://localhost:3000` to access the creative dashboard.

### 4. Running Tests

Run the complete test suite (50+ assertions covering storyboards, continuity, evidence gathering, reliability keys, clip reviews, final reviews, and publishing gates):

```powershell
cd backend
py -m pytest tests/ -v
```

---

## n8n Integration Workflows

The `n8n/workflows/` directory contains complete workflow templates for orchestrating dev tasks:
- `shorts_create_project_dev.json` — Initial project creation and Scene 1 prompt generation.
- `shorts_generate_next_dev.json` — Automates prompt loop execution on approvals.
- `shorts_notify_dev.json` — Human-in-the-loop alert routing.
- `shorts_publish_dev.json` — Orchestrates asset downloads, mock YouTube upload integrations, and API callback updates.
- `shorts_error_handler_dev.json` — Global pipeline failure catching.

