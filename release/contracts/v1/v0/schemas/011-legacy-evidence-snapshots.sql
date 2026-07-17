-- Harness schema migration 011
-- Immutable evidence embedded while conservatively reconciling legacy
-- improvement rows whose source trace/intervention has no stable uid.

CREATE TABLE legacy_evidence_snapshot (
    uid                  TEXT PRIMARY KEY,
    source_kind          TEXT NOT NULL CHECK(source_kind IN ('trace','intervention')),
    source_local_id      INTEGER,
    evidence_fingerprint TEXT NOT NULL,
    canonical_payload    TEXT NOT NULL,
    captured_at          TEXT NOT NULL,
    UNIQUE(source_kind, evidence_fingerprint)
);

INSERT INTO schema_version (version) VALUES (11);
