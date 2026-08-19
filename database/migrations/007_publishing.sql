-- Final review and YouTube upload jobs for Phase 8 publishing automation.

CREATE TABLE IF NOT EXISTS final_review_events (
    event_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    manifest_id VARCHAR(64) NOT NULL,
    decision VARCHAR(20) NOT NULL CHECK (decision IN ('approved', 'rejected')),
    actor VARCHAR(200) NOT NULL,
    comment TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS clip_review_events (
    event_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    scene_number INTEGER NOT NULL,
    artifact_id VARCHAR(64) NOT NULL,
    decision VARCHAR(20) NOT NULL CHECK (decision IN ('approved', 'rejected')),
    actor VARCHAR(200) NOT NULL,
    comment TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS youtube_upload_jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    manifest_id VARCHAR(64) NOT NULL,
    status VARCHAR(30) NOT NULL,
    youtube_video_id VARCHAR(50) NOT NULL DEFAULT '',
    upload_attempts INTEGER NOT NULL DEFAULT 0,
    error_class VARCHAR(50) NOT NULL DEFAULT '',
    upload_checksum VARCHAR(64) NOT NULL,
    published_at TIMESTAMPTZ,
    youtube_url VARCHAR(500) NOT NULL DEFAULT '',
    error VARCHAR(1000) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    UNIQUE(project_id, upload_checksum)
);

CREATE INDEX IF NOT EXISTS idx_youtube_upload_jobs_project ON youtube_upload_jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_final_review_events_project ON final_review_events(project_id);
