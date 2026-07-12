#!/usr/bin/env bash
set -euo pipefail

[[ $# == 1 ]] || {
  echo "usage: $0 harness-cli-vX.Y.Z" >&2
  exit 2
}

tag=$1
[[ "$tag" =~ ^harness-cli-v([0-9]+\.[0-9]+\.[0-9]+)$ ]] || {
  echo "release identity rejected: invalid stable tag: $tag" >&2
  exit 1
}
expected_version=${BASH_REMATCH[1]}

git rev-parse --verify --quiet "refs/tags/$tag^{commit}" >/dev/null || {
  echo "release identity rejected: tag is not present in the checkout: $tag" >&2
  exit 1
}

head_sha=$(git rev-parse HEAD)
tag_sha=$(git rev-parse "refs/tags/$tag^{commit}")
[[ "$head_sha" == "$tag_sha" ]] || {
  echo "release identity rejected: HEAD $head_sha does not match $tag $tag_sha" >&2
  exit 1
}

actual_version=$(awk -F'"' '/^version = / {print $2; exit}' crates/harness-cli/Cargo.toml)
[[ "$actual_version" == "$expected_version" ]] || {
  echo "release identity rejected: tag version $expected_version does not match crate version $actual_version" >&2
  exit 1
}

echo "release identity passed: tag=$tag source_commit=$head_sha crate_version=$actual_version"
