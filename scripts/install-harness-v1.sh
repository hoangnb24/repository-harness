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

artifact_name=${artifact##*/}
artifact_parent=${artifact%/*}
[ "$artifact_parent" != "$artifact" ] || artifact_parent=.
artifact_parent=$(cd -P "$artifact_parent" 2>/dev/null && pwd -P) || fail "artifact parent is unavailable"
artifact=$artifact_parent/$artifact_name
checksum_name=${checksum##*/}
checksum_parent=${checksum%/*}
[ "$checksum_parent" != "$checksum" ] || checksum_parent=.
checksum_parent=$(cd -P "$checksum_parent" 2>/dev/null && pwd -P) || fail "checksum parent is unavailable"
checksum=$checksum_parent/$checksum_name
[ -f "$artifact" ] && [ ! -L "$artifact" ] || fail "artifact changed before authentication"
[ -f "$checksum" ] && [ ! -L "$checksum" ] || fail "checksum changed before authentication"

# Authentication is deliberately first. No platform branch or executable
# invocation occurs until the externally supplied checksum matches exact bytes.
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

# Pin the intended repository and destination directories before copying. A
# component that is a link, non-directory, non-canonical alias, or concurrently
# substituted cannot redirect publication outside this pinned directory chain.
while [ "$directory" != "/" ] && [ "${directory%/}" != "$directory" ]; do
  directory=${directory%/}
done
case "$directory" in
  /*) ;;
  *) fail "target directory must be an absolute path" ;;
esac
[ "$directory" != "/" ] || fail "target directory cannot be the filesystem root"
[ -d "$directory" ] && [ ! -L "$directory" ] || fail "target directory is missing or is a link"
directory_name=${directory##*/}
directory_parent=${directory%/*}
[ -n "$directory_parent" ] || directory_parent=/
parent_physical=$(cd -P "$directory_parent" 2>/dev/null && pwd -P) || fail "target parent cannot be pinned"
case "$parent_physical" in
  /) expected_root=/$directory_name ;;
  *) expected_root=$parent_physical/$directory_name ;;
esac
root_physical=$(cd -P "$directory" 2>/dev/null && pwd -P) || fail "target directory cannot be pinned"
[ "$root_physical" = "$expected_root" ] || fail "target directory escaped its physical parent"
cd "$root_physical" || fail "target directory cannot be pinned"

if [ -e scripts ] || [ -L scripts ]; then
  [ -d scripts ] && [ ! -L scripts ] || fail "destination component scripts is unsafe"
else
  mkdir scripts || fail "destination component scripts could not be created"
fi
cd scripts || fail "destination component scripts could not be pinned"
[ "$(pwd -P)" = "$root_physical/scripts" ] || fail "destination component scripts escaped the target root"

if [ -e bin ] || [ -L bin ]; then
  [ -d bin ] && [ ! -L bin ] || fail "destination component scripts/bin is unsafe"
else
  mkdir bin || fail "destination component scripts/bin could not be created"
fi
cd bin || fail "destination component scripts/bin could not be pinned"
[ "$(pwd -P)" = "$root_physical/scripts/bin" ] || fail "destination component scripts/bin escaped the target root"

destination=harness
[ ! -e "$destination" ] && [ ! -L "$destination" ] || fail "destination already exists"
temporary=.harness-v1-install.$$
[ ! -e "$temporary" ] && [ ! -L "$temporary" ] || fail "temporary install path already exists"
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
