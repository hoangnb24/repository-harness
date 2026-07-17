# US-108 V1 Install, Update, And Recovery

Status: **Implemented and locally validated; orchestrator acceptance pending**

## Current Behavior

US-107 supplies the accepted Phase 2 V1 core. It authenticates independently
rooted release material, audits an existing V1 manifest, and emits a stable
preview for `install`, `update`, or `scaffold`. It deliberately refuses every
write because Phase 2 has no backup, journal, durable flush, atomic manifest,
resume, or rollback implementation.

The permanent command grammar is already fixed to six commands:

```text
install update audit scaffold status version
```

Recovery is represented by `--resume` and `--rollback` options on the command
that owns the operation. A seventh command would violate the Phase 1 contract.
The repository-local CLI also has no promoted production payload or trust
adapter, so live production mutation remains unavailable even after the Phase
3 execution boundary exists.

## Target Behavior

After this story, a caller that injects a Phase 2-authenticated
`VerifiedRelease` and the Phase 3 mutation port can:

1. preview the exact managed writes, recovery journal, backups, and resulting
   manifest;
2. confirm those exact operations with
   `--non-interactive --accept-preview-sha256 <digest>`;
3. write only managed files or the interior of a declared managed block;
4. preserve target-owned bytes and use `never-auto-patch` for them;
5. apply `replace-if-base` only when current bytes still equal the recorded
   base, and emit deterministic base/current/candidate three-way review data
   when they do not;
6. create exclusive backups and staged post-images before target mutation;
7. persist an ignored tool-local journal under
   `.harness/recovery/<operation-id>/journal.json`;
8. fsync temporary files, backups, staged images, journals, and containing
   directories before an atomic rename;
9. commit `.harness/manifest.json` last, only after structural validation and a
   final confirmation-digest recheck; and
10. safely resume incomplete command-owned steps or roll back only exact
    matching post-images.

Concrete crash example:

1. Update stages authenticated candidate bytes and backs up `docs/policy.md`.
2. It atomically replaces that managed file and records the applied step.
3. The process dies before the manifest rename.
4. The old manifest cannot claim the new release succeeded. Read-only status
   finds the applying journal and reports `mutation=recovery-required`; audit
   remains read-only and may report the old-manifest/partial-target mismatch as
   invalid.
5. `harness update --resume <operation-id>` reauthenticates the release,
   verifies journal ownership plus current post-image digests, performs only
   incomplete steps, revalidates the candidate manifest, and commits it last.
6. If a maintainer edited `docs/policy.md` after the crash, resume and rollback
   both stop with exit 4 instead of overwriting that edit.

An exact confirmed rerun is also read-only once a durable journal exists. It
returns recovery-required and names the owning command's resume/rollback
options instead of rebuilding against partial targets or replaying writes.

## Affected Users

- Repository owners installing or updating managed V1 seed-kit assets.
- Brownfield owners whose mapped or target-owned content must survive intact.
- V1 maintainers reviewing filesystem durability and recovery evidence.
- Release maintainers, whose production promotion gate remains closed.

## Affected Product Docs

- `docs/REFACTOR_PLAN.md`
- `docs/contracts/v1/**`
- `docs/stories/US-105-harness-v1-implementation/**`
- `docs/stories/US-107-v1-pure-core/**`
- this US-108 packet

## Non-Goals

- A V0 reader, SQLite/changeset dependency, bridge command, migrate alias, or
  conversion/archive workflow.
- Production keys, a promoted payload/bootstrap adapter, publishing, tagging,
  or changes to the guarded release workflow.
- Non-Unix safe-handle equivalence or five-platform release proof; those stay
  behind Phase 7.
- Target-tool execution, language/framework detection, generators, or stack
  inference.
- Durable task/run/trace state or mutation of `.harness/changesets`, Harness DB
  files, local conversion archives, or `repomix-output.xml`.
- Automatic merging of a changed managed surface. A conflict is review output,
  never permission to patch.
