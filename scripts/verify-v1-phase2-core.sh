#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"

for command in cargo python3; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Phase 2 core verification requires: $command" >&2
    exit 1
  }
done

cargo test --quiet --locked --package harness-core
cargo build --quiet --locked --package harness-core --bin harness
cargo build --quiet --locked --package harness-v0-migrate --bin harness-v0-migrate
mkdir -p scripts/bin
install -m 755 target/debug/harness scripts/bin/harness
install -m 755 target/debug/harness-v0-migrate scripts/bin/harness-v0-migrate

python3 scripts/verify_v1_phase2_core.py
