-- Phase 1 reliability records for integration retries and operational auditability.
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key VARCHAR(200) PRIMARY KEY,
    operation VARCHAR(100) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    response_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS integration_events (
    event_id VARCHAR(64) PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    project_id VARCHAR(36),
    request_id VARCHAR(200),
    metadata_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_integration_events_project_id ON integration_events(project_id);
CREATE INDEX IF NOT EXISTS idx_integration_events_request_id ON integration_events(request_id);
