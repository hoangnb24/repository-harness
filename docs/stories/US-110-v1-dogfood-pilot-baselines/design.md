# US-110 V1 Dogfood And Pilot Baselines Design

Status: **Repository-owned Phase 5 candidate implemented / live pilot gate intentionally blocked**

## Domain Model

`DogfoodMap` binds one immutable Repository Harness source revision to useful
existing paths. Each entry records role, path, activation, ownership, origin,
required state, update policy, Git blob, and SHA-256. All mapped paths are
`target-owned`, `brownfield-mapped`, and `never-auto-patch`.

Cause and effect: `docs/decisions/README.md` is already the useful decision
index. Mapping it as `decisions` tells an agent where decisions live. Target
ownership then prevents an update from rewriting it, and its pinned source
blob proves the map describes the accepted Phase 4 tree rather than a later
guess.

`PilotCard` is one immutable P0-P7 revision-1 scenario. A card fixes the
prompt, applicability rule, acceptance tests, mandatory failures, and required
evidence. `CardCatalog` lists exactly eight cards and binds their file bytes by
SHA-256. A catalog digest change invalidates every enrollment and owner
signature that names the earlier catalog.

`PilotEnrollment` belongs to an external repository owner. It contains an
authorized scope and evidence reference, one full 40-character immutable Git
commit, evidence custody, an unrelated-pilot declaration, and the exact card
catalog digest. Repository Harness cannot create this record on an owner's
behalf.

`EnvironmentLock` fixes model, reasoning, operating system, architecture, tool
names and versions, enabled tools, permissions, evaluator, fixture digests,
and acceptance commands. Its digest is canonical JSON with
`environment_sha256` omitted. If any condition changes, the digest changes and
the baseline must rerun.

`Eligibility` contains exactly P0-P7. Each card is `eligible` or
`inapplicable`; inapplicability requires a non-empty evaluator finding. Thus a
pilot without V0 records P1 as inapplicable with inspected-path evidence rather
than deleting P1.

`InterventionLog` records actor, timestamp, fixed taxonomy, reason, whole
minutes, outcome effect, and card. Totals contain event count and minutes both
globally and grouped by card and taxonomy. The verifier recomputes every total
from events, so an evaluator cannot report only correction time while omitting
setup or evidence relay.

`BaselineResult` is closed to `run_kind=baseline`. It repeats enrollment
revision, card catalog digest, environment digest, exact P0-P7 outcomes,
evidence references, intervention log, and its canonical digest. Unknown
candidate fields fail schema validation, so a Phase 6 candidate run cannot be
relabeled as a baseline.

`OwnerSignature` names the card catalog, exact subject SHA-256, signer,
authority reference, algorithm, time, and non-empty detached signature. The
repository verifier proves structural presence and digest binding. The pilot
owner retains cryptographic algorithm selection and verification evidence at
the authority reference; Repository Harness does not fabricate a key or sign
for the owner.

## Application Flow

Repository-owned flow:

1. Load the Phase 5 Draft 2020-12 schemas and fixed card catalog.
2. Recompute every card digest and reject a missing, extra, duplicated, or
   changed card.
3. Resolve the dogfood source commit, Git blob, and SHA-256 for each mapped
   path.
4. Inspect the diff from that source and reject every rename or deletion of a
   mapped path.
5. Execute the allowlisted ordinary-task `rg` and Git checks and reject any
   invocation of `harness install`, `update`, `audit`, `scaffold`, `status`,
   `version`, or `--version`.
6. Exercise one synthetic test-only positive packet and ten negative
   mutations. Synthetic names and signatures are visibly non-evidence.

Future authorized-pilot flow:

1. The owner supplies authorization, immutable revision, and custody.
2. The evaluator locks the complete environment before a baseline run.
3. The owner signs the exact fixed catalog digest.
4. Eligibility records P0-P7, including written inapplicability.
5. The baseline runs every eligible card and records every intervention.
6. The verifier recomputes digests/totals and compares all repeated identities.
7. Only when two unrelated packets pass may the evidence index become
   `complete`; independent review still decides Phase 5 acceptance.

## Interface Contract

The executable interface is:

```text
scripts/verify-v1-phase5-evidence.sh
scripts/verify-v1-phase5-evidence.sh --dogfood-only
scripts/verify-v1-phase5-evidence.sh --require-pilot-baselines
```

Default and dogfood-only success return 0. A malformed repository-owned
contract returns 1. The live pilot gate returns 2 when authorization or
evidence is incomplete and prints each blocker. It returns 0 only after at
least two complete unrelated pilot packets validate.

The machine-readable file schemas are under
`tests/evals/v1-phase5/schemas/`. Pilot custody directories referenced by
`evidence/index.json` contain exactly `enrollment.json`, `environment.json`,
`eligibility.json`, `card-set.signature.json`, `interventions.json`, and
`baseline-result.json`.

## Data Model

All records are tracked UTF-8 JSON files. No SQLite database, migration,
changeset, task row, telemetry record, or V1 manifest is created. Digests are
lowercase SHA-256. Environment and result self-digests use sorted-key compact
UTF-8 JSON with the digest field omitted; catalog/card digests bind exact file
bytes.

Pilot evidence is append/review data owned jointly by its repository owner and
evaluator. Changing an immutable revision, signed catalog, locked environment,
or result digest is rejection, not an update-in-place. A legitimate condition
change creates a new reviewed run and does not overwrite the baseline used for
comparison.

## UI / Platform Impact

There is no browser, mobile, desktop, service, installer, core CLI, or bridge
behavior change. The verifier uses Python 3, Git, `rg`, and repository files;
its repository-owned proof is platform-neutral except for the existing shell
wrapper. Five-platform artifact behavior remains Phase 7.

## Observability

The verifier prints numbered proof groups and a final count. Negative fixtures
are expected to fail inside the test group; accepting one fails the verifier.
Live-evidence mode prints blockers to stderr and returns 2. It does not log raw
pilot commands, secrets, or telemetry outside owner-approved evidence files.

## Alternatives Considered

1. Move Repository Harness documents to V1 default paths. Rejected because the
   current paths are already useful and moves would damage history and links.
2. Create a second V1-only documentation tree. Rejected because duplicate
   sources would make ordinary discovery ambiguous.
3. Require `harness audit` before ordinary tasks. Rejected because V1 is an
   optional seed kit during normal work and audit is not a task gate.
4. Add placeholder pilots with sample commits or signatures. Rejected because
   a plausible placeholder could be mistaken for real owner evidence.
5. Make the live evidence command pass with zero pilots. Rejected because it
   would turn schema presence into Phase 5 behavioral proof.
6. Add a JSON Schema dependency. Rejected because the closed schemas use a
   small deterministic subset that the standard-library verifier can enforce;
   dependency and lockfile churn adds no evidence value here.
