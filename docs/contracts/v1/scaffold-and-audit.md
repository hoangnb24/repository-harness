# Scaffold And Deterministic Audit Contract

Contract: `repository-harness-scaffold-audit/v1`

## Safe paths

All paths are UTF-8, NFC-normalized, repository-relative, `/`-separated, and
nonempty. Reject absolute, UNC, drive-prefixed, backslash-containing, NUL or
control-character paths; empty, `.` or `..` components; trailing dot/space;
`:` in any component (including Windows alternate-data-stream spellings such
as `docs/README.md:evil`); Windows device names; and `.git` or undeclared
`.harness` destinations.

Before reading or writing, walk from an already opened repository-root handle.
Open every component without following links, reject symlinks/reparse points,
and record file identity. Capture keeps the pinned root, ancestor, and final
descriptors open; pre/copy/post identity, size, and exact-byte SHA-256 are read
through the same final handle. Each namespace component is then compared
through its pinned parent descriptor. A swapped ancestor or final path
therefore becomes exit 4 with zero commit, even if the replacement has the
expected bytes.

Build one collision key per path using Unicode NFC plus platform-independent
case folding. Two entries with the same collision key are invalid on every
platform. This prevents a release containing both `docs/Readme.md` and
`docs/README.md` from behaving differently on macOS, Linux, and Windows.

## Managed markers

A managed block has exactly one opening marker
`<!-- repository-harness:v1:begin:<marker-id> -->` and one closing marker
`<!-- repository-harness:v1:end:<marker-id> -->`, in that order, with no nested
Harness marker. Marker IDs are ASCII lower kebab-case and unique per manifest.
Only bytes strictly between that pair are managed. Missing, duplicate,
reordered, nested, or path-mismatched markers are invalid.

Scaffold never edits an existing target-owned file. It creates one explicitly
selected artifact only when every ancestor and collision check passes. A
pre-existing path produces conflict, even when contents happen to match.

## Links and anchors

Audit examines Markdown links only in declared managed surfaces. Relative links
are resolved from the containing file after percent-decoding once, must remain
inside the repository, and must resolve through the same no-follow walk. Anchor
IDs use the contract's deterministic GitHub-style lowercasing and hyphenation
over NFC heading text; duplicate generated anchors are invalid unless the link
uses the deterministic numeric suffix.

External URLs, target-owned prose, and unavailable feedback routes are not
fetched or semantically judged. A required relative link missing from a managed
index is invalid; a prose statement that could be clearer is outside audit.

## Exact bytes and deterministic order

SHA-256 always covers exact file bytes. Audit never normalizes LF/CRLF, adds a
newline, decodes then re-encodes text for digest comparison, or trusts metadata
in place of bytes. Reports sort by normalized collision key, then exact UTF-8
path bytes, rule ID, and asset ID.

## Zero process execution

Audit and status perform filesystem reads and pure parsing only. They may not
start Git, shells, compilers, tests, linters, CI clients, link checkers,
deployment tools, language package managers, hooks, daemons, or target
executables. Scaffold also executes zero processes. It writes declared bytes;
it does not run a generator afterward.

Example: a managed document says `cargo test` is the target's proof command.
Audit may validate that the link and marker containing that declaration are
structurally present. It must not execute `cargo`, so identical inputs have
identical outputs and audit cannot run target-controlled code.
