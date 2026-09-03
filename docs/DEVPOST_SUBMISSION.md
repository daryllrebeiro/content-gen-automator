# 🎬 Devpost Submission Copy — Agentic Cinema: The Blockbuster Hackathon

---

### Project Title
**ContentGenAutomator Studio: Governed Agentic Cinema**

### Short Tagline (One Sentence)
An enterprise-governed cinematic production studio coordinating a 7-agent Google Cloud ADK hierarchy with fail-closed IBM watsonx brand safety guardrails and cryptographic compliance certificates.

---

### Links
* 🌐 **Live Production (Google Cloud Run):** `[GCP_URL]`
* ⚡ **Instant Fork & Run (Replit):** `[REPLIT_URL]`
* 🎥 **Demo Walkthrough Video:** `[VIDEO_URL]`
* 💻 **GitHub Repository:** [https://github.com/daryllrebeiro/ContentGenAutomator](https://github.com/daryllrebeiro/ContentGenAutomator)
* 📜 **License:** Apache 2.0 (Open Source)

---

### 📖 About the Project

#### The Problem: Creator Fatigue Meets Enterprise Risk
Short-form video has become the dominant media format globally, yet creators and media studios face an unsustainable paradox: algorithmic distribution demands constant publishing velocity with microscopic attention spans (requiring visual cuts every 3–5 seconds and strict ~2.5 words/second narration pacing), while enterprise brands are terrified of ungoverned generative AI hallucinating false claims, violating copyrights, or producing brand-damaging outputs. Most existing "text-to-video" tools are single-prompt toys that lack narrative continuity, factual grounding, and compliance controls.

#### The Solution: ContentGenAutomator Studio
ContentGenAutomator Studio is a production-grade, stateful, multi-agent cinematic production studio built for the **Agentic Cinema: The Blockbuster Hackathon** under the **IBM watsonx Track**. It elevates prompt creation and short-form video generation into a disciplined, director-governed workflow. Instead of generating unvetted videos in a black box, the platform orchestrates a 7-agent hierarchy where every scene is grounded in verified facts, paced to exact word budgets, formatted with camera and lighting directives for generative video diffusion models, and guarded by fail-closed compliance gates.

#### How It Works: The 5-Partner Runtime Intelligence Stack
1. **Fact Grounding & Research (Parallel):** When a topic is provided, the `ResearchAgent` queries Parallel Search to extract verified factual anchors, style guidelines, and visual references.
2. **Visual & Narrative Synthesis (Google Cloud ADK & Gemini):** `OrchestratorAgent` coordinates an Agent2Agent (A2A) sequence where `ContinuityAgent` locks deterministic character seeds, `ScreenwriterAgent` drafts duration-budgeted voiceovers, and `CinematographerAgent` synthesizes volumetric lighting, rim-light accents, and camera directives for video diffusion pipelines.
3. **Fail-Closed Brand Safety (IBM watsonx):** Before any prompt enters the production rendering queue, `GovernanceAgent` executes a dual-pass audit (visual prompt + narration). If toxicity, brand safety, or copyright risk thresholds are violated, the pipeline halts immediately with an HTTP 422 error. Approved scenes receive a cryptographically signed SHA-256 compliance certificate.
4. **Telemetry & FinOps (Grafana Labs & ClickHouse):** Generation latencies and token consumptions stream via OpenLIT OTLP to Grafana Cloud, while ClickHouse records high-throughput scene events and render latencies into columnar materialized views.
5. **Distribution (YouTube & Replit):** Once all 7 automated publishing gates pass and human final review is granted, the project is packaged into signed export manifests and uploaded directly to YouTube Shorts.

---

### 🛠️ How We Built It

* **Agent Orchestration (Google Cloud ADK):** Built on the official `google-adk 2.8.0` SDK. All 7 agents (`OrchestratorAgent`, `ResearchAgent`, `ScreenwriterAgent`, `CinematographerAgent`, `ContinuityAgent`, `GovernanceAgent`, `PublishingAgent`) subclass `google.adk.agents.LlmAgent`. Every agent exposes typed domain tool contracts (`draft_narration_tool`, `synthesize_visual_prompt_tool`, `register_seed_tool`, etc.), with `OrchestratorAgent` employing delegation tools for typed A2A handoffs.
* **AI Model Engine (Gemini Enterprise):** Powered by Google Gemini 2.5 Flash (`google-genai 1.75.0` / `2.0+`) for multimodal reasoning, scene pacing, and diffusion visual directives.
* **Brand Governance Gate (IBM watsonx):** Primary hackathon track spine. The governance adapter enforces customizable policy packs (*General Audience*, *Kids & Family*, *Mature Documentary*). While the codebase includes live API client integration for IBM watsonx.governance endpoints (`ibm_governance.py`), in this deployed submission instance without external enterprise IBM SaaS credentials configured, the governance gate runs our deterministic local rule-based safety and copyright heuristics. This ensures unbypassable fail-closed governance (halting generation with HTTP 422 upon violation) with 100% reliability and zero external latency.
* **Observability (Grafana Labs):** Real-time AI metrics exposition via Prometheus `/metrics` and OpenLIT OTLP exporter tracking token consumption, latency percentiles, and governance decision ratios.
* **Analytics (ClickHouse Cloud):** High-throughput columnar analytics engine with materialized views (`studio_command_center_mv`) and anomaly detection window functions.
* **Full-Stack Application:** FastAPI backend with strict state machine contracts, 94 automated unit and contract tests, and a Next.js 15 cyber-neon studio UI with Grafana Faro RUM, real-time FinOps budget progress bar, Governance Advisor pre-submission badges, Policy Pack Manager, and interactive Cryptographic Certificate Verifier.
* **Dual Cloud Deployments (Google Cloud Run & Replit):**
  - **Google Cloud Run (Primary Production):** Serverless container deployment with Artifact Registry, automated Cloud Build pipelines, Secret Manager credentials injection (`GEMINI_API_KEY`), and free-tier infrastructure guardrails (`min-instances=0`, `max-instances=3`).
  - **Replit (Instant Fork & Run):** Configured via `.replit` and `replit_start.sh` for one-click developer evaluation in the browser with full cross-origin support and verified live deployment.

---

### 🧗 Challenges We Ran Into (The Engineering Reality)

Our biggest technical challenge was avoiding the trap of "superficial integration." In early development passes, we had code that appeared integrated at a high level but relied on custom wrapper classes rather than the official platform primitives, or fell back to mock branches because environment defaults weren't strictly wired. 

Rather than sweeping this under the rug, we subjected our codebase to strict adversarial audits:
1. **Migrating to Official ADK Primitives:** We refactored all 7 custom agent classes to inherit directly from official `google.adk.agents.LlmAgent`, wired typed tool contracts into every agent, and verified that A2A handoffs execute cleanly while preserving all domain finite-state machine (FSM) invariants.
2. **Fail-Closed Governance Verification:** We ensured that the IBM watsonx governance gate isn't just an advisory badge in the UI, but an active, blocking dependency in the FastAPI route (`/api/projects/{id}/prompts/first`) that halts generation with HTTP 422 if safety or copyright risk thresholds fail. We also implemented deep semantic synonym expansion and polar contradiction detection to block subtle inverted hallucinations that evade standard n-gram checks.
3. **Durable Multi-Agent Memory:** We migrated in-memory memory banks to real atomic file persistence (`.storage/memory_bank.json` and `.storage/vertex_search_datastore.json`), proven with a dedicated cross-process verification suite (`verify_memory_persistence.py`).
4. **Production Deployment Nuances:** We resolved container port mapping, CORS origins, and strict authentication behavior across development and production modes (`APP_ENV=production`) to guarantee that the live Replit deployment runs identically to local development.

This rigorous verification cycle significantly improved our architecture's defensibility, reliability, and code quality.

---

### 🚀 What's Next for ContentGenAutomator Studio

1. **Vertex AI Agent Engine Hosted Cluster:** Transition from running the ADK multi-agent tree in-process to deploying it to hosted Google Cloud Vertex AI Reasoning Engine instances using our verified `deploy-agent-engine.sh` and `agent_engine_client.py` delegation bridge.
2. **Live Generative Video API Hooks:** Connect direct API webhooks to Kling AI, Runway Gen-3, and Gemini Omni Flash generative video endpoints to replace simulated video callbacks with live diffusion rendering.
3. **Enterprise watsonx Multi-Tenancy:** Add multi-tenant IBM watsonx governance dashboards allowing corporate compliance teams to enforce custom brand risk policies across distributed content creation teams.
