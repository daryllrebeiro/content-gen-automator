-- Human approval decisions are immutable records tied to a prompt scene.
CREATE TABLE IF NOT EXISTS approval_events (
    event_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    scene_number INTEGER NOT NULL,
    decision VARCHAR(20) NOT NULL CHECK (decision IN ('approved', 'rejected')),
    actor VARCHAR(120) NOT NULL,
    comment VARCHAR(1000) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_approval_events_project_scene ON approval_events(project_id, scene_number);
