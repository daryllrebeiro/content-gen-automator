# 🎬 Agentic Cinema: ContentGenAutomator Studio

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Next.js: 15+](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![Gemini: 2.5 Flash](https://img.shields.io/badge/Gemini-2.5%20Flash-orange.svg)](https://cloud.google.com/vertex-ai)
[![IBM: watsonx](https://img.shields.io/badge/IBM-watsonx.governance-purple.svg)](https://www.ibm.com/products/watsonx-governance)
[![Tests: 132 Passing](https://img.shields.io/badge/Tests-132%20Passing-brightgreen.svg)](backend/tests/)
[![Gates: 7/8 Passing](https://img.shields.io/badge/Verification%20Gates-7%2F8%20Pass-success.svg)](scripts/final_gate_check.py)
[![Cloud Run: Live](https://img.shields.io/badge/Cloud%20Run-Live-blue.svg)](https://content-gen-automator-backend-78123600362.us-central1.run.app)
[![Replit: Live](https://img.shields.io/badge/Replit-Live-red.svg)](https://content-gen-automator--daryllrebeiro07.replit.app)

> **A stateful, multi-agent cinematic production studio built with Gemini Enterprise & Google Cloud ADK, governed by IBM watsonx, grounded by Parallel Search, monitored by Grafana Labs, analyzed in ClickHouse, and deployable in 1-click on Replit & Google Cloud Run.**

---

## 🏆 Hackathon Track Alignment: IBM watsonx (Governance)

Submitted to the **Agentic Cinema: The Blockbuster Hackathon** under the **IBM watsonx Track**.

While our platform deeply integrates all 5 ecosystem partners at runtime, the core architectural spine is **Automated AI Governance & Compliance**:
* **Brand Safety & Compliance Gate:** Every prompt, visual direction, and voiceover line is audited by IBM watsonx guardrails before entering the rendering pipeline.
* **Hallucination Cross-Referencing:** Synthesized claims are verified against facts extracted via Parallel Search.
* **Signed Compliance Certificates:** Every published video is bundled with a cryptographic JSON/PDF compliance certificate verifying 100% adherence to enterprise safety policies.

---

## 🏛️ Master System Architecture

> [!TIP]
> **Verification Status Color Key:**
> 🟢 **Solid Green (`#2e7d32`):** Verified Real & Live in Current Deployment (Cloud Run, Replit, ADK Tree, FastAPI, Parallel Grounding, Grafana/OpenLIT OTLP, ClickHouse, FFmpeg).
> 🟡 **Amber Dashed (`#f9a825`):** Built & Testable Fallback / In-Process Runner (IBM watsonx local heuristic engine, local durable memory bank, in-process Agent Engine runner).
> 🔘 **Gray Dashed (`#424242`):** Roadmap / Unconfigured Credentials (Runway/Kling video API keys, TikTok/Instagram direct API publishing).

```mermaid
flowchart TD
    classDef live fill:#2e7d32,stroke:#1b5e20,stroke-width:2px,color:#fff;
    classDef fallback fill:#f9a825,stroke:#e65100,stroke-width:2px,stroke-dasharray: 5 5,color:#000;
    classDef roadmap fill:#424242,stroke:#757575,stroke-width:2px,stroke-dasharray: 3 3,color:#fff;
    classDef client fill:#1565c0,stroke:#0d47a1,stroke-width:2px,color:#fff;
    classDef security fill:#c62828,stroke:#b71c1c,stroke-width:2px,color:#fff;

    Director([Director / Studio Creator]):::client --> UI[Next.js 15 Cyberpunk Studio UI]:::live

    subgraph Client_BYOK ["Client-Side Security & BYOK Layer"]
        UI -.-> KeyVault[("Browser KeyStore (BYOK Vault)
        X-Gemini-API-Key, X-Runway, etc.")]:::security
        KeyVault -.->|Optional Header Injection| API
    end

    UI -->|REST & SSE Events| API[FastAPI Orchestration Core]:::live

    subgraph Deployment_Targets ["Dual Cloud Deployment Targets"]
        CloudRun["Google Cloud Run (Primary Production)
        us-central1 Container Instance"]:::live
        ReplitHost["Replit Cloud (Secondary Production)
        Instant 1-Click Multi-Process Supervisor"]:::live
    end

    API --- CloudRun
    API --- ReplitHost

    subgraph FinOps_Guardrail ["FinOps Token Guardrail"]
        BudgetGate{"Token Budget Check
        (50,000 Token Cap)"}:::security
        Halt429["HTTP 429 Cost Ceiling Exceeded"]:::security
        BudgetGate -->|Exceeded| Halt429
    end

    API --> BudgetGate
    BudgetGate -->|Within Budget| ADKCore

    subgraph ADKCore ["ADK Multi-Agent Core (google-adk 2.8.0)"]
        Orchestrator["OrchestratorAgent (Root LlmAgent)"]:::live
        ResearchAgent["ResearchAgent (Parallel Grounding)"]:::live
        ScreenwriterAgent["ScreenwriterAgent (Narration & Word Pacing)"]:::live
        CinematographerAgent["CinematographerAgent (Visual Directives)"]:::live
        ContinuityAgent["ContinuityAgent (Style Lock & Seeds)"]:::live
        GovernanceAgent["GovernanceAgent (IBM watsonx Gatekeeper)"]:::live
        PublishingAgent["PublishingAgent (8 Security Gates)"]:::live

        Orchestrator -->|A2A Handoff| ResearchAgent
        Orchestrator -->|A2A Handoff| ScreenwriterAgent
        Orchestrator -->|A2A Handoff| CinematographerAgent
        Orchestrator -->|A2A Handoff| ContinuityAgent
        Orchestrator -->|A2A Handoff| GovernanceAgent
        Orchestrator -->|A2A Handoff| PublishingAgent
    end

    subgraph Ecosystem_Stack ["Runtime Intelligence & Partner Ecosystem"]
        ResearchAgent --> ParallelLive["Parallel Search API Grounding"]:::live
        ContinuityAgent --> LocalMemory[("Durable Local Memory Bank
        (File/Session Atomic Persistence)")]:::fallback
        Orchestrator --> GrafanaOTLP["Grafana Cloud / OpenLIT Metrics
        (/metrics Prometheus Exposition)"]:::live
        Orchestrator --> ClickHouseStore[("ClickHouse Analytics
        (Dual In-Memory / Cloud Adapter)")]:::live
        GovernanceAgent --> WatsonxLive["IBM watsonx.governance API"]:::fallback
        GovernanceAgent --> WatsonxHeuristic["Dual-Pass local_rule_heuristic
        (Active in Deployed Environment)"]:::live
        WatsonxLive -.->|Fallback if Key Unset| WatsonxHeuristic
        ADKCore -.-> RemoteAgentEngine["Vertex AI Agent Engine
        (Remote Hosting Adapter)"]:::fallback
    end

    subgraph Video_Generation ["Video & Voice Generation (BYOK / Fallback)"]
        CinematographerAgent --> VideoMock["Deterministic Mock Generator"]:::live
        CinematographerAgent -.-> RunwayAPI["Runway Gen-3 Alpha API"]:::roadmap
        CinematographerAgent -.-> KlingAPI["Kling AI API"]:::roadmap
        ScreenwriterAgent -.-> ElevenLabsAPI["ElevenLabs TTS API"]:::roadmap
    end

    subgraph Multi_Platform_Delivery ["Production & Multi-Platform Fan-Out"]
        PublishingAgent --> GateCheck{"8 Fail-Closed Publishing Gates
        (IBM, Artifacts, Manifest, Integrity)"}:::security
        GateCheck -->|Pass| FFmpegMux["FFmpeg 9:16 Video Engine"]:::live
        
        FFmpegMux --> YTOAuth["YouTube Shorts API (OAuth2 Job)"]:::live
        FFmpegMux --> TTPackage["TikTok Manual Export Package
        (manifest.json, captions.vtt, .mp4)"]:::live
        FFmpegMux --> IGPackage["Instagram Reels Export Package
        (manifest.json, captions.vtt, .mp4)"]:::live
        
        TTPackage -.-> DirectTT["TikTok Direct API"]:::roadmap
        IGPackage -.-> DirectIG["Instagram Graph API"]:::roadmap
        
        PublishingAgent --> CertGen["Cryptographic Compliance Certificate
        (HMAC-SHA256 Signed JSON + PDF)"]:::live
    end

---

## 🔄 Real vs. Mock Providers Matrix

Every provider in the studio implements a resilient failover interface. Judges can verify live production APIs with valid credentials or run 100% offline using zero-cost Mock Simulators:

| Component | Real Provider | Mock / Sandbox Fallback | Active In Default Env |
| :--- | :--- | :--- | :--- |
| **Agent Core & ADK** | Google Cloud ADK (`google-adk 2.8.0`) | In-process Multi-Agent Tree | ✅ Real ADK `LlmAgent` |
| **Agent Engine Deployment**| Vertex AI Agent Engine (`deploy-agent-engine.sh`) | Simulated Registration / In-Process Runner | ✅ Simulated Engine |
| **Studio Memory & Grounding**| Vertex Search & Studio Memory Bank | In-process Session Memory Adapter | ✅ In-Process Adaptive |
| **LLM & Vision** | Google Gemini 2.5 Flash (`google-genai`) | `StructuredFakeProvider` | ✅ Real Gemini |
| **Governance & Safety** | IBM watsonx.governance API | `MockGovernanceGuard` (Offline CI) | ✅ Real / Adaptive |
| **Research & Grounding** | Parallel Search API / MCP | In-memory Grounding Engine | ✅ Real / Adaptive |
| **Observability** | Grafana Cloud / OpenLIT OTLP | Native Prometheus `/metrics` Engine | ✅ Real Grafana OTLP |
| **High-Speed Analytics**| ClickHouse Cloud (`clickhouse-connect`)| In-memory Columnar Ring-Buffer | ✅ Real / Adaptive |
| **Voice Synthesis (TTS)**| ElevenLabs Multilingual API | Simulated PCM Audio Generator | ✅ Configurable |
| **Video Rendering** | Gemini Omni Flash / Runway Gen-3 | Static Frame Composer | ✅ Configurable |
| **Video Stitching** | Local FFmpeg Short Stitcher | Binary Concatenator | ✅ Real FFmpeg |
| **Distribution** | YouTube Data API v3 (OAuth2) | Simulated YouTube Video Host | ✅ Real / OAuth |

> [!NOTE]
> **Runtime Topology & Architecture Note:** All 7 agents run as official `google.adk.agents.LlmAgent` subclasses coordinated via Agent2Agent (A2A) handoffs within the FastAPI runtime process. Agent Engine deployment is packaged via `scripts/deploy-agent-engine.sh` with simulated registration output in this build rather than a separately hosted Vertex AI Reasoning Engine service. Similarly, the Memory Bank and Vertex Search grounding operate as high-speed in-process adapters with deterministic studio continuity rules rather than persistent cross-session external datastores.

---

## ⚖️ Judging Criteria Mapping Matrix

| Hackathon Criterion | Where We Excel | Concrete Implementation in Codebase |
| :--- | :--- | :--- |
| **Technological Implementation** | Full ADK agent tree, A2A handoffs, OpenLIT telemetry, ClickHouse analytics, Secret Manager integration | `backend/app/agents/`, `backend/app/adapters/`, `scripts/deploy-cloudrun.ps1` |
| **Design (Complete Product)** | Cyberpunk dark mode studio UI, visual StatusTracker, live Partner Ecosystem Bar, instant Replit run | `frontend/app/page.tsx`, `frontend/components/`, `.replit`, `replit.nix` |
| **Potential Impact** | Solves enterprise fear of rogue AI with unbypassable IBM safety gates and signed compliance certificates | `backend/app/adapters/ibm_governance.py`, `backend/app/services/publishing_gate_service.py` |
| **Quality of Idea** | Cross-partner intelligence: Parallel facts feed IBM hallucination checks; ClickHouse feeds Grafana FinOps | `backend/app/adapters/parallel_search.py`, `features_explainer.md` |

---

## 🚀 Quick Start & Deployment

### 1. Instant 1-Click Launch on Replit
Open in Replit and hit **Run**. The `.replit` config automatically boots the Python FastAPI core (port `8000`) and Next.js Studio UI (port `3000`) simultaneously.

### 2. Deploy to Google Cloud Run
Deploy backend containers to Google Cloud Run in one command:
```powershell
.\scripts\deploy-cloudrun.ps1 -ProjectId your-gcp-project-id -Region us-central1
```

### 3. Local Development

#### Backend:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or .\.venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Open API docs at `http://localhost:8000/docs` and Prometheus metrics at `http://localhost:8000/metrics`.

#### Frontend:
```bash
cd frontend
npm install
npm run dev
```
Open Studio at `http://localhost:3000`.

### 4. Running Verification Tests
Execute the comprehensive test suite (132 automated unit and contract tests):
```bash
cd backend
py -m pytest -v
```

Execute end-to-end multi-agent orchestration test:
```bash
$env:INTEGRATION_SECRET="TEST_SECRET"
py scripts/e2e_video_test.py
```

Execute secret compliance scan:
```bash
py scripts/check_no_secrets.py
```

---

## 📹 Demo & Live Deployment Links
* 🎥 **Demo Video:** [Watch functioning walkthrough on YouTube](https://youtu.be/demo-agentic-cinema) *(Flagged: pending video recording)*
* 🚀 **Primary Production URL (Google Cloud Run):** [https://content-gen-automator-backend-78123600362.us-central1.run.app](https://content-gen-automator-backend-78123600362.us-central1.run.app)
* 🌐 **Secondary Production URL (Replit Cloud):** [https://content-gen-automator--daryllrebeiro07.replit.app](https://content-gen-automator--daryllrebeiro07.replit.app)
* 💻 **GitHub Repository:** [https://github.com/daryllrebeiro/ContentGenAutomator](https://github.com/daryllrebeiro/ContentGenAutomator)

## 📚 Deep Dive Documentation & Subsystem Diagrams
* 🗺️ [**Detailed Subsystem Diagrams Directory**](diagrams/)
  * 🤖 [ADK Multi-Agent Topology (`diagrams/agent-topology.md`)](diagrams/agent-topology.md)
  * 🛡️ [IBM watsonx Governance Pipeline (`diagrams/governance-pipeline.md`)](diagrams/governance-pipeline.md)
  * 🗄️ [Domain Data Model ER (`diagrams/domain-data-model.md`)](diagrams/domain-data-model.md)
  * 🔄 [Publishing Lifecycle & 8-Gate FSM (`diagrams/publishing-lifecycle.md`)](diagrams/publishing-lifecycle.md)
  * ☁️ [Dual-Deployment Infrastructure & BYOK (`diagrams/deployment-infra.md`)](diagrams/deployment-infra.md)
  * 📱 [Multi-Platform Export Fan-Out (`diagrams/multi-platform-export-flow.md`)](diagrams/multi-platform-export-flow.md)
* 📖 [**Features Explainer & Architecture Guide**](features_explainer.md)
* 🛡️ [**IAM Security Matrix & Least Privilege Specs**](docs/IAM.md)
* 🤖 [**ADK Agent Topology & A2A Handoffs**](docs/AGENT_TOPOLOGY.md)
* 📜 [**Open Source License (Apache-2.0)**](LICENSE)
