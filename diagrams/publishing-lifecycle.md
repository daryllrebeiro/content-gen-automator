# Project Publishing Lifecycle & 8-Gate FSM

The studio strictly enforces a 12-state Finite State Machine (`ProjectStatus` in `backend/app/domain/project.py`) to prevent illegal lifecycle jumps. Before any video can be published or distributed, `backend/app/services/publishing_gate_service.py` executes an 8-gate fail-closed verification pipeline; any single failed gate returns HTTP 422 and halts delivery.

```mermaid
stateDiagram-v2
    [*] --> CREATED: Initialize Studio Project
    CREATED --> INPUT_RECEIVED: Ingest Topic & Parameters
    INPUT_RECEIVED --> FACT_CHECKING: Extract & Ground Claims
    FACT_CHECKING --> STORY_CREATED: Parallel Grounding Complete
    STORY_CREATED --> SCENES_PLANNED: Narrative Arc Partitioned

    state Scene_Iteration_Loop {
        SCENES_PLANNED --> AWAITING_NEXT: Ready for Scene N
        AWAITING_NEXT --> PROMPT_APPROVAL_PENDING: Synthesize Prompts & Governance Pre-Check
        PROMPT_APPROVAL_PENDING --> APPROVED: Director / AI Gate Approves Scene
        PROMPT_APPROVAL_PENDING --> PROMPT_APPROVAL_PENDING: Reject / Request Prompt Repair
        APPROVED --> AWAITING_NEXT: More Scenes Remain
    }

    APPROVED --> COMPLETED: All Scenes Approved
    COMPLETED --> VIDEO_REVIEW_PENDING: Render Scene Clips
    
    VIDEO_REVIEW_PENDING --> VIDEO_APPROVED: All Clip Artifacts Reviewed
    VIDEO_REVIEW_PENDING --> VIDEO_REJECTED: Quality Threshold Missed

    VIDEO_APPROVED --> PUBLISHING_PENDING: Evaluate 8 Publishing Gates

    state Publishing_Gates_Evaluation {
        direction TB
        Gate1: Gate 1 - Prompt Approval per Scene [BLOCKING]
        Gate2: Gate 2 - Succeeded Production Job per Scene [BLOCKING]
        Gate3: Gate 3 - Clip Artifact Review Status == Approved [BLOCKING]
        Gate4: Gate 4 - No Contradicted Facts / IBM Clearance [BLOCKING]
        Gate5: Gate 5 - Export Manifest Created & Unexpired [BLOCKING]
        Gate6: Gate 6 - Human Final Review Signed Off [BLOCKING]
        Gate7: Gate 7 - Anti-Double Upload Lock (No active job) [BLOCKING]
        Gate8: Gate 8 - Multi-Platform Media Export Completeness [BLOCKING]
    }

    PUBLISHING_PENDING --> PUBLISHED: All 8 Gates Pass -> Dispatch Upload
    PUBLISHING_PENDING --> PUBLISH_FAILED: Any Gate Fails (HTTP 422) or API Error
    PUBLISH_FAILED --> PUBLISHING_PENDING: Retry / Re-mediate Gate Violation
    PUBLISHED --> [*]
```
