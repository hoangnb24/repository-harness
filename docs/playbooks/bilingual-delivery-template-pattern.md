# Bilingual Delivery Template Pattern

**Lifecycle:** experimental · **First use:** TBD · **Verified by:** none

How to fork harness templates into a locale variant (e.g. Vietnamese,
Japanese) without losing portability of the automation, IDs, and cross-team
references.

## When To Fork

Use this pattern when:

- Client-facing deliverables (UAT, signoff, handover, client update) must be
  in a locale. The canonical English defaults live in
  `docs/templates/delivery-closure-story/` — fork from those, never invent
  a parallel shape.
- Internal automation, IDs, tokens, and file paths should stay English so
  that cross-region teams can still read and `grep` them.

Do NOT use this for:

- Playbooks themselves — playbooks are agent-facing and stay English.
- Internal docs (`HARNESS.md`, `ARCHITECTURE.md`, decisions, story packets) —
  these are operating contract, not client deliverable.

## Split Rule

| Stays English | Localizes |
| --- | --- |
| File paths, folder names | Document titles |
| IDs and tokens (`US-014`, `US-014.REQ-001`) | Section headers visible to the client |
| Code fences, commands, env var names | Body prose addressed to the client |
| Comments inside code blocks | Table column labels visible to the client |
| Internal links (`docs/...`) | Public-facing labels in those links |

Rule of thumb: if a grep-er across regions needs to find it, keep it English.
If a client reads it, localize it.

## Fork Directory Pattern

Place locale variants next to defaults:

```text
docs/templates/
├── story.md                       # default (English)
├── high-risk-story/...            # default
├── locale-vi/
│   ├── story.md                   # Vietnamese titles + body
│   └── high-risk-story/...
└── locale-ja/                     # only if/when needed
    └── ...
```

The default `templates/*` is the source-of-truth. Locale variants are
allowed to lag the default during a transition — note staleness in a header
comment such as:

```markdown
<!-- Synced from ../story.md @ 2026-05-17. Re-sync after default updates. -->
```

## Concrete Example — Vietnamese UAT Snippet

```markdown
<!-- docs/templates/locale-vi/uat.md fragment -->

# Biên bản kiểm thử nghiệm thu UAT — US-014

| Mã kịch bản | Mô tả | Kết quả mong đợi | Ghi chú |
| --- | --- | --- | --- |
| US-014.TC-001 | Quản lý cập nhật vai trò thành viên | Vai trò mới được lưu | |
| US-014.TC-002 | Thành viên không có quyền không sửa được | Trả về lỗi 403 | |
```

The story ID (`US-014`), test IDs (`US-014.TC-001`), and HTTP status codes
stay English. The titles, descriptions, and document name localize.

## Anti-Patterns

- **Translating IDs** (`HS-014` instead of `US-014`). Breaks `grep` and
  cross-region traceability immediately.
- **Forking the whole harness into a locale repo.** Use the `locale-*`
  subdirectory instead — keeps the default in sync and avoids per-locale
  upgrade pain.
- **Mixing locales inside one file.** One file = one locale. A bilingual
  table looks tidy until a third locale appears.
- **Translating playbook content.** Playbooks are agent-facing. Translating
  them creates dialects that an agent cannot cross-reference.

## Variant Tracking

When a locale variant is shipped, log it in a single index file the org
maintains (not in the harness itself, which stays neutral):

```text
<org-repo>/docs/locales.md
- locale-vi: synced 2026-05-17 with templates/ @ commit abc123
- locale-ja: synced 2026-04-02 with templates/ @ commit def456 (stale)
```

The harness never assumes a specific locale list. The org owns its locale
inventory.

## Next Steps

- When the first regional fork happens, that team should run this pattern
  and report friction. Append `Variant` sections to this playbook as needed
  (per `docs/playbooks/README.md` variant convention).
