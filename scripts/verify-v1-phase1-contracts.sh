#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"

command -v python3 >/dev/null 2>&1 || {
  echo "Phase 1 contract verification requires python3" >&2
  exit 1
}

command -v cargo >/dev/null 2>&1 || {
  echo "Phase 1 contract verification requires cargo" >&2
  exit 1
}

# Decision 0014 deliberately preserves the generated Phase 1 conversion
# fixtures as historical evidence. Regenerating them from the superseding
# archive-only contracts would rewrite accepted bytes, so prove that this
# candidate has not modified the tracked fixture tree instead.
git diff --quiet -- tests/fixtures || {
  echo "tracked fixture bytes differ from the accepted baseline" >&2
  exit 1
}
cargo build --quiet --locked --package v1-contract-crypto
cargo build --quiet --locked --package harness-core --bin harness
cargo build --quiet --locked --package harness-v0-migrate --bin harness-v0-migrate
mkdir -p "$root/scripts/bin"
install -m 755 "$root/target/debug/harness" "$root/scripts/bin/harness"
install -m 755 "$root/target/debug/harness-v0-migrate" "$root/scripts/bin/harness-v0-migrate"
V1_CONTRACT_CRYPTO="$root/target/debug/v1-contract-crypto" \
  python3 scripts/verify_v1_phase1_contracts.py
