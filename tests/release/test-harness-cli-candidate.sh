#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT

"$root/scripts/build-harness-cli-release.sh" --out-dir "$temp/dist"
artifact=$(find "$temp/dist" -maxdepth 1 -type f -name 'harness-cli-*' ! -name '*.sha256')
checksum="$artifact.sha256"
[[ -f "$artifact" && -f "$checksum" ]]
[[ "$(find "$temp/dist" -maxdepth 1 -type f | wc -l | tr -d ' ')" == 2 ]]
(
  cd "$temp/dist"
  shasum -a 256 -c "$(basename "$checksum")" >/dev/null
)
[[ "$($artifact --version)" == "harness-cli $(awk -F\" '/^version = / {print $2; exit}' "$root/crates/harness-cli/Cargo.toml")" ]]
"$root/tests/protocol/smoke-native-artifact.sh" "$artifact"

cp "$artifact" "$temp/tampered"
printf 'tamper\n' >>"$temp/tampered"
[[ "$(shasum -a 256 "$temp/tampered" | awk '{print $1}')" != "$(awk '{print $1}' "$checksum")" ]]

echo "host Harness CLI candidate packaging, checksum, version, and protocol smoke passed"
