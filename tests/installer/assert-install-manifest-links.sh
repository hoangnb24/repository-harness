#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
core_manifest="$root/scripts/harness-install-files.txt"
cli_manifest="$root/scripts/harness-cli-install-files.txt"
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT
assets="$temp/assets"
core="$temp/core"
full="$temp/full"
platform=fixture-platform
mkdir -p "$assets"

# The compatibility installers retain both declarations; the Rust core embeds
# and is checked against the core declaration below.
[[ "$(grep -Fc 'PAYLOAD_MANIFEST="scripts/harness-install-files.txt"' "$root/scripts/install-harness.sh")" == 1 ]]
[[ "$(grep -Fc 'CLI_PAYLOAD_MANIFEST="scripts/harness-cli-install-files.txt"' "$root/scripts/install-harness.sh")" == 1 ]]
[[ "$(grep -Fc '$script:PayloadManifest = "scripts/harness-install-files.txt"' "$root/scripts/install-harness.ps1")" == 1 ]]
[[ "$(grep -Fc '$script:CliPayloadManifest = "scripts/harness-cli-install-files.txt"' "$root/scripts/install-harness.ps1")" == 1 ]]

python3 - "$root" "$core_manifest" "$cli_manifest" <<'PY'
import pathlib, sys
root = pathlib.Path(sys.argv[1])
seen = set()
for manifest_name in sys.argv[2:]:
    manifest = pathlib.Path(manifest_name)
    for number, raw in enumerate(manifest.read_text().splitlines(), 1):
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        if value.startswith("/") or ".." in pathlib.PurePosixPath(value).parts:
            raise SystemExit(f"unsafe manifest path at {manifest.name}:{number}: {value}")
        if value in seen:
            raise SystemExit(f"duplicate profile path: {value}")
        seen.add(value)
        if not (root / value).is_file():
            raise SystemExit(f"missing manifest source: {value}")
PY

printf '%s\n' '#!/usr/bin/env sh' 'exit 0' >"$assets/harness-cli-$platform"
chmod 755 "$assets/harness-cli-$platform"
(cd "$assets" && shasum -a 256 "harness-cli-$platform" >"harness-cli-$platform.sha256")

# A deliberately invalid CLI URL proves the default path never consults it.
HARNESS_CLI_BASE_URL="file://$temp/absent" \
HARNESS_CLI_PLATFORM="$platform" \
  "$root/scripts/install-harness.sh" --directory "$core" --yes >/dev/null

HARNESS_CLI_BASE_URL="file://$assets" \
HARNESS_CLI_PLATFORM="$platform" \
  "$root/scripts/install-harness.sh" --directory "$full" --with-cli --yes >/dev/null

python3 - "$core" "$full" "$core_manifest" "$cli_manifest" "$root/scripts/schema" <<'PY'
import pathlib, re, sys
core, full, core_manifest, cli_manifest, schema_root = map(pathlib.Path, sys.argv[1:])

def entries(path):
    return {
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

core_expected = entries(core_manifest)
core_runtime = {
    ".gitignore",
    ".harness-core/.gitignore",
    ".harness-core/lock",
    ".harness-core/manifest.json",
    "scripts/bin/harness",
} | {f".harness-core/base/{path}" for path in core_expected}
core_actual = {
    str(path.relative_to(core))
    for path in core.rglob("*")
    if path.is_file()
}
if core_actual != core_expected | core_runtime:
    raise SystemExit(
        f"core payload mismatch: missing={sorted((core_expected | core_runtime)-core_actual)} "
        f"extra={sorted(core_actual-(core_expected | core_runtime))}"
    )

full_required = core_expected | core_runtime | entries(cli_manifest) | {
    f"scripts/schema/{path.name}" for path in schema_root.glob("*.sql")
} | {"scripts/bin/harness-cli"}
full_actual = {
    str(path.relative_to(full))
    for path in full.rglob("*")
    if path.is_file()
}
if full_actual != full_required:
    raise SystemExit(
        f"CLI payload mismatch: missing={sorted(full_required-full_actual)} "
        f"extra={sorted(full_actual-full_required)}"
    )

pattern = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")
for install_root in (core, full):
    errors = []
    for document in install_root.rglob("*.md"):
        for target in pattern.findall(document.read_text(errors="replace")):
            target = target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            relative = target.split("#", 1)[0]
            resolved = (document.parent / relative).resolve()
            try:
                resolved.relative_to(install_root.resolve())
            except ValueError:
                errors.append(f"{document.relative_to(install_root)}: link escapes install root: {target}")
                continue
            if not resolved.exists():
                errors.append(f"{document.relative_to(install_root)}: missing local link: {target}")
    if errors:
        raise SystemExit("\n".join(errors))
PY

echo "core and CLI manifests, exact payloads, and installed links passed"
