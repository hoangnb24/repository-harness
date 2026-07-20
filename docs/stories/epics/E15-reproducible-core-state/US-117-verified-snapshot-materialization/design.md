# Design

## Tracked Tuple

```text
.harness/core-state/harness.db
.harness/core-state/manifest.json
.harness/changesets/*.changeset.jsonl
```

The manifest contains format and schema versions, the snapshot byte and logical
SHA-256 values, and sorted `{id, path, content_sha256}` entries for changesets
whose effects are already present in the snapshot.

## Materialization

```text
missing source harness.db
  -> verify manifest and baseline byte hash
  -> copy baseline to a sibling temporary database
  -> verify SQLite integrity and baseline logical hash
  -> for every sorted JSONL file:
       included id + same hash -> skip
       included id + other hash -> fail
       not included             -> apply transactionally
  -> verify current schema and core ownership
  -> atomic rename to harness.db
```

An error removes the temporary database. An existing output is never replaced.

## Security And Sanitization

Publication refuses product-owned active state, the source checkout's absolute
path, private-key material, bearer tokens, and common long-lived token shapes.
The snapshot is produced through SQLite online backup, not by copying a live
main file, and is made read-only after verification.

## Compatibility

Only a source checkout's default database uses this tracked tuple. An explicit
`HARNESS_DB_PATH` and an installed consumer continue through the existing
initialize/migrate behavior.
