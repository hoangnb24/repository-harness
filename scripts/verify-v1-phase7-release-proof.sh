#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/.." && pwd)
cd "$root"

command -v python3 >/dev/null 2>&1 || {
  echo "Phase 7 release proof verification requires: python3" >&2
  exit 1
}

python3 scripts/verify_v1_phase7_release_proof.py "$@"
