#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/../.." && pwd)
cd "$root"

python3 tests/release/test_v1_artifact_provenance.py
echo "Phase 7 GitHub/Sigstore provenance adversaries passed"
