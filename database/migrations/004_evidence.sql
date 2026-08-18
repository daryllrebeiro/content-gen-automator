-- Durable fact verification jobs and normalized evidence references.
CREATE TABLE IF NOT EXISTS fact_verification_jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    status VARCHAR(30) NOT NULL,
    claim_count INTEGER NOT NULL,
    verified_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    error VARCHAR(1000) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence_records (
    evidence_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    claim_id VARCHAR(100) NOT NULL,
    url VARCHAR(2000) NOT NULL,
    normalized_url VARCHAR(2000) NOT NULL,
    source_rank INTEGER NOT NULL,
    notes VARCHAR(1000) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_records_claim ON evidence_records(project_id, claim_id);
