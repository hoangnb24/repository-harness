#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT

mkdir -p "$temp/repo/crates/harness-cli"
cp "$root/scripts/verify-harness-cli-release-identity.sh" "$temp/repo/verify.sh"
chmod +x "$temp/repo/verify.sh"
cat >"$temp/repo/crates/harness-cli/Cargo.toml" <<'EOF'
[package]
name = "harness-cli"
version = "1.2.3"
EOF
git -C "$temp/repo" init -q
git -C "$temp/repo" config user.name "release identity test"
git -C "$temp/repo" config user.email "release-identity@example.invalid"
git -C "$temp/repo" add .
git -C "$temp/repo" commit -q -m initial
git -C "$temp/repo" tag harness-cli-v1.2.3

(cd "$temp/repo" && ./verify.sh harness-cli-v1.2.3) >/dev/null

if (cd "$temp/repo" && ./verify.sh harness-cli-v1.2.4) >/dev/null 2>&1; then
  echo "missing tag unexpectedly passed release identity" >&2
  exit 1
fi
if (cd "$temp/repo" && ./verify.sh harness-cli-v1.2.3-rc1) >/dev/null 2>&1; then
  echo "non-stable tag unexpectedly passed release identity" >&2
  exit 1
fi

git -C "$temp/repo" commit --allow-empty -q -m later
if (cd "$temp/repo" && ./verify.sh harness-cli-v1.2.3) >/dev/null 2>&1; then
  echo "tag/source mismatch unexpectedly passed release identity" >&2
  exit 1
fi

git -C "$temp/repo" tag -f harness-cli-v1.2.3 >/dev/null
sed -i.bak 's/version = "1.2.3"/version = "1.2.4"/' "$temp/repo/crates/harness-cli/Cargo.toml"
rm "$temp/repo/crates/harness-cli/Cargo.toml.bak"
git -C "$temp/repo" add crates/harness-cli/Cargo.toml
git -C "$temp/repo" commit -q -m mismatch
git -C "$temp/repo" tag -f harness-cli-v1.2.3 >/dev/null
if (cd "$temp/repo" && ./verify.sh harness-cli-v1.2.3) >/dev/null 2>&1; then
  echo "tag/version mismatch unexpectedly passed release identity" >&2
  exit 1
fi

echo "release tag, source commit, and crate version identity negatives passed"
