-- Provider-neutral production jobs and validated clip artifacts.
CREATE TABLE IF NOT EXISTS provider_jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    scene_number INTEGER NOT NULL,
    prompt_version INTEGER NOT NULL,
    job_type VARCHAR(30) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    provider_job_id VARCHAR(200) NOT NULL,
    status VARCHAR(30) NOT NULL,
    contract JSONB NOT NULL,
    artifact_id VARCHAR(64) NOT NULL DEFAULT '',
    error VARCHAR(1000) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    UNIQUE(project_id, scene_number, prompt_version)
);

CREATE TABLE IF NOT EXISTS clip_artifacts (
    artifact_id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    duration_seconds DOUBLE PRECISION NOT NULL,
    aspect_ratio VARCHAR(20) NOT NULL,
    narration_end_seconds DOUBLE PRECISION NOT NULL,
    artifact_url VARCHAR(2000) NOT NULL,
    review_status VARCHAR(40) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
