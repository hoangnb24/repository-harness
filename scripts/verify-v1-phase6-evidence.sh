#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/.." && pwd)
cd "$root"

for command in git python3 ssh-keygen; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Phase 6 evidence verification requires: $command" >&2
    exit 1
  }
done

python3 scripts/verify_v1_phase6_evidence.py "$@"
