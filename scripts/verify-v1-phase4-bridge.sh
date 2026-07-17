#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"

for command in cargo python3; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Phase 4 bridge verification requires: $command" >&2
    exit 1
  }
done

python3 scripts/verify_v1_phase4_bridge.py
