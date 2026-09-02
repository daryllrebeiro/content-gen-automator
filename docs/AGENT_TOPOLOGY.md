# 🤖 ADK Multi-Agent Topology & Agent2Agent (A2A) Protocols

This document details the multi-agent hierarchy built with the **Google Cloud Agent Development Kit (ADK)** and deployed on **Gemini Enterprise Agent Platform / Agent Engine**.

---

## Agent Hierarchy & Tool Capabilities

```
OrchestratorAgent (Root ADK LlmAgent)
├── ResearchAgent (ADK Specialist)
│   ├── parallel_search_tool() [Parallel Search API]
│   └── vertex_search_style_tool() [Vertex AI Search Datastore]
│
├── ScreenwriterAgent (ADK Specialist)
│   ├── draft_narration() [Pacing & Word-Budget Constraints]
│   └── score_pacing() [2.5 words/sec Target Validator]
│
├── CinematographerAgent (ADK Specialist)
│   ├── synthesize_visual_prompt() [Diffusion Lighting & Camera Rules]
│   └── process_moodboard_frame() [Multimodal Image Reference]
│
├── ContinuityAgent (ADK Specialist)
│   ├── fetch_character_bible() [Agent Engine Memory Bank]
│   └── register_seed() [Cross-Project Visual Seed Persistence]
│
├── GovernanceAgent (ADK Specialist)
│   ├── watsonx_audit_prompt_tool() [IBM watsonx.governance API]
│   ├── watsonx_audit_narration_tool() [Hallucination & PII Detection]
│   └── compute_risk_score() [Normalized Risk Classification]
│
└── PublishingAgent (ADK Specialist)
    ├── check_publishing_gates_tool() [7 Fail-Closed Security Gates]
    ├── generate_compliance_certificate() [Signed JSON/PDF Certificate]
    └── youtube_upload() [YouTube Data API v3 OAuth2]
```

---

## Agent2Agent (A2A) Protocol Sequence

```mermaid
sequenceDiagram
    autonumber
    participant D as Director / Studio UI
    participant O as OrchestratorAgent
    participant R as ResearchAgent
    participant C as ContinuityAgent
    participant S as ScreenwriterAgent
    participant V as CinematographerAgent
    participant G as GovernanceAgent

    D->>O: Initiate Scene Generation (Topic, Scene #, Style)
    O->>R: A2A Handoff: Ground Topic with Real-world Facts
    R-->>O: Verified Fact Claims & Visual Keywords
    O->>C: A2A Handoff: Fetch Character Bible & Visual Seed
    C-->>O: Seed Token & Appearance Invariants
    O->>S: A2A Handoff: Compose Paced Narration (~25 words)
    S-->>O: Narration Voiceover Script
    O->>V: A2A Handoff: Synthesize 4K Visual Diffusion Directives
    V-->>O: Camera Motion, Volumetric Lighting & Diffusion Prompt
    O->>G: A2A Handoff: IBM watsonx Safety & Hallucination Audit
    G-->>O: Certification Verdict (Passed / Flagged + Risk Score)
    O-->>D: Return Complete Verified Scene Proposal
```

---

## Technical Invariants
1. **Agent Proposes, FSM Disposes:** The agents reason over inputs and propose state transitions; the underlying Python Finite State Machine guarantees no illegal state jump is ever executed.
2. **Deterministic Durations:** 10s (1 scene), 20s (2 scenes), 30s (3 scenes).
3. **Cross-Project Memory Bank:** Character visual traits and brand voice guidelines persist across projects in the Director's studio portfolio.
