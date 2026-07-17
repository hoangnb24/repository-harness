-- Replay-safe links from stories to stable backlog occurrences.
CREATE TABLE story_backlog_link (
    story_id TEXT NOT NULL,
    backlog_uid TEXT NOT NULL,
    relationship TEXT NOT NULL CHECK (relationship IN ('resolves', 'references')),
    linked_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (story_id, backlog_uid),
    FOREIGN KEY (story_id) REFERENCES story(id),
    FOREIGN KEY (backlog_uid) REFERENCES backlog(uid)
);

CREATE UNIQUE INDEX story_backlog_one_resolver
  ON story_backlog_link(backlog_uid) WHERE relationship='resolves';
CREATE INDEX story_backlog_by_story ON story_backlog_link(story_id, relationship);

INSERT INTO schema_version (version) VALUES (10);
