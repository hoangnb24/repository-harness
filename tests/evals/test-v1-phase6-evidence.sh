#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/../.." && pwd)
cd "$root"

fail() {
  echo "Phase 6 focused test failed: $*" >&2
  exit 1
}

for command in git python3 ssh-keygen; do
  command -v "$command" >/dev/null 2>&1 || fail "missing command: $command"
done

scripts/verify-v1-phase6-evidence.sh --framework-only
scripts/verify-v1-phase6-evidence.sh

set +e
pending_output=$(scripts/verify-v1-phase6-evidence.sh --require-candidate-results 2>&1)
pending_exit=$?
set -e
[[ "$pending_exit" -eq 2 ]] || fail "required candidate evidence did not return pending exit 2"
[[ "$pending_output" == *"candidate evidence pending"* ]] || fail "pending result omitted blocker"

temporary=$(mktemp -d "${TMPDIR:-/tmp}/phase6-focused.XXXXXX")
trap 'rm -rf "$temporary"' EXIT
source_repository=$temporary/source
private_capture=$temporary/private-capture
mkdir -p "$source_repository/scripts/bin"

cp tests/fixtures/v1-phase4/wal-only-schema-13/harness.db "$source_repository/harness.db"
cp tests/fixtures/v1-phase4/wal-only-schema-13/harness.db-wal "$source_repository/harness.db-wal"
cp tests/fixtures/v1-phase4/wal-only-schema-13/harness.db-shm "$source_repository/harness.db-shm"
cp scripts/verify-v1-phase6-evidence.sh "$source_repository/scripts/bin/harness-cli"
chmod 700 "$source_repository/scripts/bin/harness-cli"

(
  cd "$source_repository"
  git init -q
  printf '%s\n' 'harness.db*' 'scripts/bin/harness-cli' >.gitignore
  printf '%s\n' 'synthetic warm-capture repository' >README.md
  git add .gitignore README.md
  git -c user.name=phase6-test -c user.email=phase6-test@example.invalid commit -q -m fixture
)

revision=$(git -C "$source_repository" rev-parse HEAD)
summary=$(python3 scripts/capture-v1-phase6-warm-v0.py \
  --source-root "$source_repository" \
  --destination-root "$private_capture" \
  --expected-revision "$revision" \
  --pilot-id synthetic-warm-pilot \
  --canonical-repository https://example.com/owner/synthetic.git \
  --capture-id synthetic-warm-capture \
  --captured-at 2000-01-01T00:00:00Z \
  --writers-quiesced)

[[ "$summary" != *"$temporary"* ]] || fail "capture summary leaked an absolute path"
[[ "$summary" != *"harness.db"* ]] || fail "capture summary leaked a raw filename"
[[ "$summary" != *"SQLite format"* ]] || fail "capture summary leaked raw bytes"
[[ -s "$private_capture/public-capture.json" ]] || fail "public capture manifest is missing"
[[ -s "$private_capture/standalone-backup.sqlite" ]] || fail "standalone backup is missing"

python3 - "$private_capture/public-capture.json" <<'PY'
import importlib.util
import json
from pathlib import Path
import sys

module_path = Path("scripts/verify_v1_phase6_evidence.py")
spec = importlib.util.spec_from_file_location("phase6_verifier", module_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
module.validate(manifest, module.schema("warm-v0-capture"), "synthetic warm capture")
assert manifest["capture_sha256"] == module.canonical_digest(manifest, "capture_sha256")
assert manifest["source_unchanged"] is True
assert {item["category"] for item in manifest["artifacts"]} >= {"database", "wal", "shm", "v0-cli"}
PY

set +e
unsafe_output=$(python3 scripts/capture-v1-phase6-warm-v0.py \
  --source-root "$source_repository" \
  --destination-root "$source_repository/unsafe-capture" \
  --expected-revision "$revision" \
  --pilot-id synthetic-warm-pilot \
  --canonical-repository https://example.com/owner/synthetic.git \
  --capture-id synthetic-unsafe-capture \
  --captured-at 2000-01-01T00:00:00Z \
  --writers-quiesced 2>&1)
unsafe_exit=$?
set -e
[[ "$unsafe_exit" -eq 1 ]] || fail "capture accepted a destination inside the live source"
[[ "$unsafe_output" == *"must be external"* ]] || fail "unsafe-destination rejection was not explicit"

set +e
uncoordinated_output=$(python3 scripts/capture-v1-phase6-warm-v0.py \
  --source-root "$source_repository" \
  --destination-root "$temporary/uncoordinated" \
  --expected-revision "$revision" \
  --pilot-id synthetic-warm-pilot \
  --canonical-repository https://example.com/owner/synthetic.git \
  --capture-id synthetic-uncoordinated-capture \
  --captured-at 2000-01-01T00:00:00Z 2>&1)
uncoordinated_exit=$?
set -e
[[ "$uncoordinated_exit" -eq 1 ]] || fail "capture omitted writer-quiescence requirement"
[[ "$uncoordinated_output" == *"--writers-quiesced is required"* ]] || fail "writer-quiescence rejection was not explicit"

python3 - "$private_capture/standalone-backup.sqlite" <<'PY'
import sqlite3
from pathlib import Path
import sys

connection = sqlite3.connect(
    f"file:{Path(sys.argv[1])}?mode=ro&immutable=1", uri=True
)
try:
    result = connection.execute("PRAGMA integrity_check").fetchone()
    assert result == ("ok",)
finally:
    connection.close()
PY

git -C "$source_repository" diff --quiet
git -C "$source_repository" diff --cached --quiet

echo "Phase 6 focused framework and synthetic capture tests passed"
