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
manifest = module.load_json(Path(sys.argv[1]))
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

python3 - "$source_repository" "$temporary" "$revision" <<'PY'
import os
from pathlib import Path
import shutil
import subprocess
import sys

source = Path(sys.argv[1])
root = Path(sys.argv[2])
revision = sys.argv[3]
wal_bytes = (source / "harness.db-wal").read_bytes()
shm_bytes = (source / "harness.db-shm").read_bytes()


def run_case(name, prepare, mutate):
    case_source = root / f"namespace-{name}"
    destination = root / f"capture-{name}"
    shutil.copytree(source, case_source, symlinks=True)
    prepare(case_source)
    ready_read, ready_write = os.pipe()
    continue_read, continue_write = os.pipe()
    environment = dict(os.environ)
    environment["HARNESS_PHASE6_CAPTURE_TEST_READY_FD"] = str(ready_write)
    environment["HARNESS_PHASE6_CAPTURE_TEST_CONTINUE_FD"] = str(continue_read)
    process = subprocess.Popen(
        [
            sys.executable,
            "scripts/capture-v1-phase6-warm-v0.py",
            "--source-root", str(case_source),
            "--destination-root", str(destination),
            "--expected-revision", revision,
            "--pilot-id", "synthetic-warm-pilot",
            "--canonical-repository", "https://example.com/owner/synthetic.git",
            "--capture-id", f"synthetic-{name}-capture",
            "--captured-at", "2000-01-01T00:00:00Z",
            "--writers-quiesced",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
        pass_fds=(ready_write, continue_read),
    )
    os.close(ready_write)
    os.close(continue_read)
    try:
        assert os.read(ready_read, 1) == b"1", f"{name}: capture hook was not reached"
        mutate(case_source)
        os.write(continue_write, b"1")
    finally:
        os.close(ready_read)
        os.close(continue_write)
    stdout, stderr = process.communicate(timeout=30)
    assert process.returncode == 1, f"{name}: mutation accepted: {stdout} {stderr}"
    assert "namespace changed" in stderr or "directory token changed" in stderr, (
        f"{name}: rejection was not an anchored namespace failure: {stderr}"
    )


run_case(
    "new-wal",
    lambda case: (case / "harness.db-wal").unlink(),
    lambda case: (case / "harness.db-wal").write_bytes(wal_bytes),
)
run_case(
    "unlink-wal",
    lambda case: None,
    lambda case: (case / "harness.db-wal").unlink(),
)


def replace_wal(case):
    replacement = case / "replacement-wal"
    replacement.write_bytes(wal_bytes)
    os.replace(replacement, case / "harness.db-wal")


run_case("replace-wal", lambda case: None, replace_wal)


def transient_shm(case):
    path = case / "harness.db-shm"
    path.write_bytes(shm_bytes)
    path.unlink()


run_case(
    "transient-shm",
    lambda case: (case / "harness.db-shm").unlink(),
    transient_shm,
)
PY

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
