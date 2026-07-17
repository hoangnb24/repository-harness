-- Harness schema migration 007
-- Direct Harness story dependency edges for generic work-graph derivation.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS story_dependency (
    story_id        TEXT NOT NULL REFERENCES story(id) ON DELETE CASCADE,
    blocks_story_id TEXT NOT NULL REFERENCES story(id) ON DELETE CASCADE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (story_id, blocks_story_id),
    CHECK (story_id <> blocks_story_id)
);

CREATE INDEX IF NOT EXISTS idx_story_dependency_blocker
    ON story_dependency(blocks_story_id);

INSERT INTO schema_version (version) VALUES (7);
