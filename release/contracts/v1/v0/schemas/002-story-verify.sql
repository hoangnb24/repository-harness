-- Harness v0 schema - migration 002
-- Story-level mechanical verification.

ALTER TABLE story ADD COLUMN verify_command TEXT;
ALTER TABLE story ADD COLUMN last_verified_at TEXT;
ALTER TABLE story ADD COLUMN last_verified_result TEXT
    CHECK(last_verified_result IN ('pass','fail') OR last_verified_result IS NULL);

INSERT INTO schema_version (version) VALUES (2);
