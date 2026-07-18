#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/.." && pwd)
cd "$root"

for command in git python3 rg ssh-keygen; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Phase 5 evidence verification requires: $command" >&2
    exit 1
  }
done

python3 scripts/verify_v1_phase5_evidence.py "$@"
