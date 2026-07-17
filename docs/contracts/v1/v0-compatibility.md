# Frozen V0 Compatibility Contract

Contract: `repository-harness-v0-input/v1`

## Supported schema range

The first bridge may read exactly V0 `schema_version` 1 through 13 inclusive.
The exact SQL bytes are frozen under `release/contracts/v1/v0/schemas/`; their
names and SHA-256 values are in `v0-schema-inventory.json`. Those copies are
bridge-only compatibility material. They are prohibited from the V1 core
payload.

The reader never applies a missing migration to a source. A schema below 1,
above 13, with gaps, with a hash/shape not represented by the frozen sequence,
or with unrecognized objects is unsupported/invalid as specified by the input
matrix and is preserved unchanged.

## Changeset parser range

Recognized changesets are UTF-8 JSON Lines. Blank lines are ignored. The first
nonblank value must be `changeset.header` version 1 with a nonblank `run_id` and
integer `base_schema_version` in 1–13. Operation versions are exactly 1 or 2;
missing `version` means 1, matching the current parser. The complete closed
operation/version matrix is `v0-changeset-operation-matrix.json`.

An unknown operation, version 0 or 3, duplicate JSON member, invalid UTF-8,
malformed line, or header outside the supported schema range fails closed. The
bridge reports it and preserves the source; it never skips an unknown
operation.

## Public V0 feature freeze

`v0-feature-snapshot.json` and `v0-command-paths.txt` freeze the current public
binary identity, protocol/capability declaration, required environment, schema
range, and 50 public command paths. Phase 1 tests compare these files with the
existing parser/source manifest. New V0 top-level or nested commands,
capabilities, changeset operations/versions, schemas, or installer payload
features are rejected unless a later explicit compatibility decision changes
the freeze.

This freeze does not remove or alter current V0 behavior. It prevents Phase 1
from accidentally expanding V0 while preparing V1.

## Data dispositions

`v0-data-categories.json` assigns every durable table and recognized filesystem
category one disposition. Database records and raw recovery evidence are
bridge-only legacy inputs; V0 binaries, schemas, operational changesets, and
lifecycle payloads are forbidden in V1 core; useful target-owned documents are
mapped without importing their V0 operational records.

Example: a V0 `story` row is exported as categorized legacy evidence and stays
in the archive. It does not become a V1 task record. An existing useful
`docs/ARCHITECTURE.md` may be mapped target-owned by normal V1 install, which
does not move or automatically rewrite it. Under Decision 0014 the bridge performs no mapping
at all: normal fresh V1 install may adopt the repository file, while the V0 row
remains only in archive/export evidence.
