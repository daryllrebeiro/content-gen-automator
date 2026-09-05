# ADK Multi-Agent Topology & A2A Handoff Subsystem

The multi-agent core is built with the official **Google Cloud Agent Development Kit (`google-adk 2.8.0`)**, running 7 specialized agents that subclass `google.adk.agents.LlmAgent`. In the active production deployment on Google Cloud Run and Replit, all 7 agents execute in-process within the FastAPI container using direct Agent2Agent (A2A) tool delegations; remote hosting on Vertex AI Agent Engine is built as an adapter with an automated in-process runner fallback.

```mermaid
flowchart TD
    classDef live fill:#2e7d32,stroke:#1b5e20,stroke-width:2px,color:#fff;
    classDef fallback fill:#f9a825,stroke:#e65100,stroke-width:2px,stroke-dasharray: 5 5,color:#000;
    classDef client fill:#1565c0,stroke:#0d47a1,stroke-width:2px,color:#fff;

    Client([Director UI / API Request]):::client --> Orchestrator

    subgraph ADK_Tree ["Google Cloud ADK (google-adk 2.8.0) Multi-Agent Tree"]
        Orchestrator["OrchestratorAgent (Root LlmAgent)
        Tools (6):
        - delegate_research_task
        - delegate_screenplay_task
        - delegate_cinematography_task
        - delegate_continuity_lock_task
        - delegate_governance_audit_task
        - delegate_publishing_gates_task"]:::live

        Research["ResearchAgent
        Tools (2):
        - parallel_search_tool
        - vertex_search_style_tool"]:::live

        Screenwriter["ScreenwriterAgent
        Tools (1):
        - draft_narration_tool"]:::live

        Cinematographer["CinematographerAgent
        Tools (1):
        - synthesize_visual_prompt_tool"]:::live

        Continuity["ContinuityAgent
        Tools (3):
        - register_seed_tool
        - fetch_character_bible_tool
        - fetch_continuity_lock_tool"]:::live

        Governance["GovernanceAgent
        Tools (2):
        - watsonx_audit_prompt_tool
        - watsonx_audit_narration_tool"]:::live

        Publishing["PublishingAgent
        Tools (1):
        - check_publishing_gates_tool"]:::live

        Orchestrator -->|A2A Task 1| Research
        Orchestrator -->|A2A Task 2| Screenwriter
        Orchestrator -->|A2A Task 3| Cinematographer
        Orchestrator -->|A2A Task 4| Continuity
        Orchestrator -->|A2A Task 5| Governance
        Orchestrator -->|A2A Task 6| Publishing
    end

    subgraph Runtime_Target ["Execution Runtime"]
        InProcess["In-Process ADK Coordinator
        (Verified Live on Cloud Run & Replit)"]:::live
        AgentEngine["Vertex AI Agent Engine Hosting
        (Adapter Built / In-Process Runner Fallback)"]:::fallback
    end

    ADK_Tree -.->|Active Runtime| InProcess
    ADK_Tree -.->|Optional Target| AgentEngine
```
