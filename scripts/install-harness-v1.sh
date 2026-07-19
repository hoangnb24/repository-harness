#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "Harness V1 installer refused: $*" >&2
  exit 1
}

artifact=
checksum=
platform=
directory=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --artifact|--checksum|--platform|--directory)
      [ "$#" -ge 2 ] || fail "$1 requires a value"
      case "$1" in
        --artifact) artifact=$2 ;;
        --checksum) checksum=$2 ;;
        --platform) platform=$2 ;;
        --directory) directory=$2 ;;
      esac
      shift 2
      ;;
    *) fail "unknown argument: $1" ;;
  esac
done

[ -n "$artifact" ] && [ -n "$checksum" ] && [ -n "$platform" ] && [ -n "$directory" ] ||
  fail "--artifact, --checksum, --platform, and --directory are required"
[ -f "$artifact" ] && [ ! -L "$artifact" ] || fail "artifact is missing or is a link"
[ -f "$checksum" ] && [ ! -L "$checksum" ] || fail "checksum is missing or is a link"

# Authentication is deliberately first. No platform branch or executable
# invocation occurs until the externally supplied checksum matches exact bytes.
artifact_name=${artifact##*/}
[ "$(wc -l <"$checksum" | tr -d ' ')" = 1 ] || fail "checksum must contain exactly one newline-terminated record"
checksum_record=$(sed -n '1p' "$checksum")
expected=${checksum_record%%  *}
case "$expected" in
  *[!0-9a-f]*|'') fail "checksum digest must be lowercase SHA-256" ;;
esac
[ "${#expected}" -eq 64 ] || fail "checksum digest must be lowercase SHA-256"
[ "$checksum_record" = "$expected  $artifact_name" ] || fail "checksum must bind the exact artifact filename"
if command -v shasum >/dev/null 2>&1; then
  actual=$(shasum -a 256 "$artifact" | awk '{print $1}')
elif command -v sha256sum >/dev/null 2>&1; then
  actual=$(sha256sum "$artifact" | awk '{print $1}')
else
  fail "no SHA-256 implementation is available"
fi
[ "$actual" = "$expected" ] || fail "artifact checksum mismatch"

system=$(uname -s)
machine=$(uname -m)
case "$system/$machine" in
  Darwin/arm64|Darwin/aarch64) native=macos-arm64 ;;
  Darwin/x86_64) native=macos-x64 ;;
  Linux/x86_64|Linux/amd64) native=linux-x64 ;;
  Linux/aarch64|Linux/arm64) native=linux-arm64 ;;
  *) fail "unsupported native platform: $system/$machine" ;;
esac
[ "$platform" = "$native" ] || fail "platform identity mismatch: expected $native"
case "$artifact_name" in
  harness-"$platform") ;;
  *) fail "artifact filename does not match platform identity" ;;
esac

destination=$directory/scripts/bin/harness
mkdir -p "$directory/scripts/bin"
[ ! -e "$destination" ] && [ ! -L "$destination" ] || fail "destination already exists"
temporary=$directory/scripts/bin/.harness-v1-install.$$
[ ! -e "$temporary" ] || fail "temporary install path already exists"
trap 'if [ -n "${temporary:-}" ] && [ -f "$temporary" ]; then mv "$temporary" "$temporary.failed"; fi' EXIT HUP INT TERM
cp "$artifact" "$temporary"
chmod 755 "$temporary"
installed=$(shasum -a 256 "$temporary" 2>/dev/null | awk '{print $1}') ||
  installed=$(sha256sum "$temporary" | awk '{print $1}')
[ "$installed" = "$expected" ] || fail "installed copy changed after authentication"
ln "$temporary" "$destination" || fail "destination appeared during install"
unlink "$temporary"
temporary=
echo "Installed checksum-verified Harness V1 artifact at scripts/bin/harness; provenance and platform acceptance remain unclaimed."
