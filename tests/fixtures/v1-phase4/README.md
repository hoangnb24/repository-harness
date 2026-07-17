# V1 Phase 4 immutable V0 fixtures

`generate.py` replays the frozen release-contract SQL bytes into one database
for every supported schema version. The generated inventory binds every file
to SHA-256. Tests always copy these directories before use.

`wal-only-schema-13` is captured while a reader prevents checkpointing, so the
committed `wal-only-committed-row` exists in `harness.db-wal` rather than the
copied main database. `harness.db-shm` is retained for forensic proof only.

The schema-13 fixture also includes a valid frozen-grammar changeset, recognized
provenance, and unknown `.harness/foreign-tool.bin` bytes. The bridge must
capture the recognized inputs and preserve, but not claim, the foreign bytes.
