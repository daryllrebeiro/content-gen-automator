-- Initial PostgreSQL shape for the MVP.
-- SQLAlchemy also creates this shape automatically for local development.
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(36) PRIMARY KEY,
    topic VARCHAR(500) NOT NULL,
    duration_seconds INTEGER NOT NULL,
    status VARCHAR(40) NOT NULL,
    current_scene_number INTEGER NOT NULL DEFAULT 0,
    input_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    story_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    continuity_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    facts_data JSONB NOT NULL DEFAULT '[]'::jsonb,
    scenes_data JSONB NOT NULL DEFAULT '[]'::jsonb,
    prompts_data JSONB NOT NULL DEFAULT '[]'::jsonb,
    prompt_history_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

