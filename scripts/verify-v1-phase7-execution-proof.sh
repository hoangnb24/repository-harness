#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/.." && pwd)
cd "$root"
python3 scripts/verify_v1_phase7_execution_proof.py "$@"
