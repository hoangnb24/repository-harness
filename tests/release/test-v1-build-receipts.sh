#!/usr/bin/env bash
set -euo pipefail

root=$(cd "${BASH_SOURCE[0]%/*}/../.." && pwd)
cd "$root"

starting_git_status=$(git status --short --untracked-files=all)
python3 tests/release/test_v1_build_receipts.py
ending_git_status=$(git status --short --untracked-files=all)

if [[ "$ending_git_status" != "$starting_git_status" ]]; then
  printf 'V1 build-receipt focused tests changed repository status\nbefore:\n%s\nafter:\n%s\n' \
    "$starting_git_status" "$ending_git_status" >&2
  exit 1
fi

echo "V1 native build-receipt capture/verifier adversaries passed without platform acceptance"
