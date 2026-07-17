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

python3 tests/fixtures/v1-phase1/generate.py --check
cargo build --quiet --locked --package v1-contract-crypto
V1_CONTRACT_CRYPTO="$root/target/debug/v1-contract-crypto" \
  python3 scripts/verify_v1_phase1_contracts.py
