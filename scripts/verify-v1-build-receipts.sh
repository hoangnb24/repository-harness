#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/.." && pwd)
cd "$root"

python_command=python3
if ! command -v "$python_command" >/dev/null 2>&1; then
  python_command=python
fi
command -v "$python_command" >/dev/null 2>&1 || {
  echo "V1 build receipt verification requires: python3" >&2
  exit 1
}

exec "$python_command" scripts/verify_v1_build_receipts.py "$@"
