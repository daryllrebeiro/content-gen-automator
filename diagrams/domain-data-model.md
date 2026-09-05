# Domain Data Model & Persistence Architecture

The domain data model is orchestrated in `backend/app/domain/project.py` and backed by the SQLAlchemy persistence layer in `backend/app/repositories/sql.py`. State transitions and nested multi-platform deliverables are stored using structured relational tables with versioned JSON payload contracts for scene bibles, multi-platform exports, and audit trails.

```mermaid
erDiagram
    ProjectRecord ||--o{ ApprovalEventRecord : "audits & approves"
    ProjectRecord ||--o{ ProductionJobRecord : "generates clips"
    ProjectRecord ||--o{ ExportManifestRecord : "packages"
    ProjectRecord ||--o{ PlatformExport : "fans out to"
    ProjectRecord ||--o{ ComplianceCertificate : "certified by"
    ProductionJobRecord ||--o| ClipArtifactRecord : "produces"
    ExportManifestRecord ||--o{ YouTubeUploadJobRecord : "distributes via"
    StudioPreset }o--o{ ProjectRecord : "configures initial"

    ProjectRecord {
        string id PK "UUID string"
        string topic "Short title and theme"
        int duration_seconds "10, 20, or 30 seconds"
        string status "12-state FSM enum"
        int current_scene_number "Pointer to active scene"
        json input_data "Facts, platforms, budget, model tier"
        json story_data "Hook, central claim, ending"
        json continuity_data "Style, palette, character bible"
        json facts_data "Extracted fact claims"
        json scenes_data "Planned scene outlines"
        json prompts_data "Active video prompts"
        json prompt_history_data "Prompt revisions and repairs"
        datetime created_at "Creation timestamp"
        datetime updated_at "Last update timestamp"
    }

    PlatformExport {
        string platform "YOUTUBE_SHORTS, TIKTOK, INSTAGRAM_REELS"
        string aspect_ratio "9:16 vertical standard"
        string output_asset_ref "Path to rendered MP4"
        string export_status "PENDING, COMPLETED, FAILED"
        string publish_status "NOT_STARTED, QUEUED, PUBLISHED"
        string publish_asset_ref "External platform URL/ID"
        json publish_metadata "Captions, tags, description"
    }

    ApprovalEventRecord {
        string event_id PK "Unique hash (24 chars)"
        string project_id FK "References ProjectRecord"
        int scene_number "Target scene"
        string decision "approved or rejected"
        string actor "Human director or AI system"
        string comment "Audit / review notes"
        datetime created_at "Event timestamp"
    }

    ComplianceCertificate {
        string certificate_id PK "CERT-IBM-GOV-XXXXXXXXXXXX"
        string project_id FK "References ProjectRecord"
        string manifest_id FK "References ExportManifest"
        string topic "Project topic"
        string governance_provider "IBM watsonx.governance"
        string policy_pack_applied "enterprise_strict, brand_safe"
        string overall_compliance_verdict "CERTIFIED_COMPLIANT"
        float composite_risk_score "Average risk (0.0 to 1.0)"
        string signature_hash "HMAC-SHA256 digest"
        string signature_algorithm "HMAC-SHA256"
        string certified_at "ISO-8601 UTC timestamp"
    }

    StudioPreset {
        string id PK "System or custom preset ID"
        string name "Display name"
        string description "Operational summary"
        string category "fast_draft, viral_launch, enterprise_safe"
        int default_duration "Duration seconds"
        list target_platforms "Platform list"
        string model_tier "flagship or ultra"
        string video_provider "mock, runway, kling, gemini_omni"
        string tts_provider "mock, elevenlabs"
        string policy_pack "enterprise_strict, brand_safe"
    }

    ProductionJobRecord {
        string job_id PK "UUID"
        string project_id FK "References ProjectRecord"
        int scene_number "Target scene number"
        int prompt_version "Prompt revision used"
        string job_type "clip_render"
        string provider "mock, gemini_omni, runway, kling"
        string status "QUEUED, RUNNING, SUCCEEDED, FAILED"
        string artifact_id "References ClipArtifact"
        datetime created_at "Job creation timestamp"
    }

    ClipArtifactRecord {
        string artifact_id PK "UUID"
        string job_id FK "References ProductionJob"
        string checksum "SHA-256 asset hash"
        float duration_seconds "Actual video duration"
        string aspect_ratio "9:16 vertical"
        string artifact_url "Local file or GCS URL"
        string review_status "pending, approved, rejected"
    }

    ExportManifestRecord {
        string manifest_id PK "UUID"
        string project_id FK "References ProjectRecord"
        string package_version "Semantic version"
        string checksum "SHA-256 package hash"
        string markdown "Production report markdown"
        datetime created_at "Creation timestamp"
        datetime expires_at "Expiration timestamp (TTL)"
    }

    YouTubeUploadJobRecord {
        string job_id PK "UUID"
        string project_id FK "References ProjectRecord"
        string manifest_id FK "References ExportManifest"
        string status "QUEUED, UPLOADING, PUBLISHED, FAILED"
        string youtube_video_id "YouTube Short ID"
        string youtube_url "Live Short URL"
        string upload_checksum "Payload verification hash"
        datetime created_at "Upload start timestamp"
    }
```
