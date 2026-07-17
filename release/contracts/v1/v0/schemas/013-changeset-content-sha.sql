-- Harness schema migration 013
-- Bind an applied changeset identity to the exact bytes that were accepted.

ALTER TABLE changeset_applied ADD COLUMN content_sha256 TEXT;

INSERT INTO schema_version (version) VALUES (13);
