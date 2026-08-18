-- Immutable export packages and retryable delivery jobs.
CREATE TABLE IF NOT EXISTS export_manifests (
    manifest_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    package_version VARCHAR(50) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    markdown TEXT NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS delivery_jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    manifest_id VARCHAR(64) NOT NULL,
    status VARCHAR(30) NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    error VARCHAR(1000) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_delivery_jobs_manifest ON delivery_jobs(manifest_id);
