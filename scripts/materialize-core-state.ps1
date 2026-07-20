param(
    [string]$Database = $env:HARNESS_DB_PATH,
    [string]$Cli = $env:HARNESS_CLI,
    [string]$Manifest = $env:HARNESS_CORE_MANIFEST,
    [string]$Changesets = $env:HARNESS_CHANGESET_DIR,
    [string]$StateRoot = $env:HARNESS_CORE_STATE_ROOT
)

$ErrorActionPreference = "Stop"
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
if ([string]::IsNullOrWhiteSpace($StateRoot)) { $StateRoot = $root }
$StateRoot = [System.IO.Path]::GetFullPath($StateRoot)
if ([string]::IsNullOrWhiteSpace($Database)) { $Database = Join-Path $root "harness.db" }
if ([string]::IsNullOrWhiteSpace($Cli)) { $Cli = Join-Path $root "scripts/bin/harness-cli.exe" }
if ([string]::IsNullOrWhiteSpace($Manifest)) { $Manifest = Join-Path $StateRoot ".harness/core-state/manifest.json" }
if ([string]::IsNullOrWhiteSpace($Changesets)) { $Changesets = Join-Path $StateRoot ".harness/changesets" }
$Database = [System.IO.Path]::GetFullPath($Database)
if (Test-Path $Database) { throw "Core-state materialization failed: output already exists: $Database" }
foreach ($path in @($Cli, $Manifest)) {
    if (!(Test-Path $path)) { throw "Core-state materialization failed: missing input: $path" }
}

$model = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
if ($model.format_version -ne 1 -or $model.snapshot.path -ne ".harness/core-state/harness.db" -or
    $model.snapshot.file_sha256 -notmatch '^[0-9a-f]{64}$' -or
    $model.snapshot.logical_sha256 -notmatch '^[0-9a-f]{64}$') {
    throw "Core-state materialization failed: manifest structure is invalid"
}
$snapshot = Join-Path $StateRoot $model.snapshot.path
if (!(Test-Path $snapshot)) { throw "Core-state materialization failed: snapshot is missing: $snapshot" }
$actualHash = (Get-FileHash -LiteralPath $snapshot -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $model.snapshot.file_sha256) {
    throw "Core-state materialization failed: snapshot SHA-256 mismatch"
}

$parent = Split-Path -Parent $Database
New-Item -ItemType Directory -Force -Path $parent | Out-Null
$temporary = Join-Path $parent (".harness-materialize." + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temporary | Out-Null
$candidate = Join-Path $temporary "harness.db"
$probe = Join-Path $temporary "probe.db"
try {
    Copy-Item -LiteralPath $snapshot -Destination $candidate
    [System.IO.File]::SetAttributes($candidate, [System.IO.FileAttributes]::Normal)
    $env:HARNESS_REPO_ROOT = $root
    $env:HARNESS_DB_PATH = $candidate
    $probeResult = (& $Cli db snapshot --output $probe --json | ConvertFrom-Json).result
    if ($LASTEXITCODE -ne 0 -or $probeResult.source_logical_sha256 -ne $model.snapshot.logical_sha256) {
        throw "Core-state materialization failed: snapshot logical SHA-256 mismatch"
    }
    Remove-Item -LiteralPath $probe -Force

    $includedById = @{}
    foreach ($entry in $model.included_changesets) {
        if ($includedById.ContainsKey($entry.id)) { throw "Core-state materialization failed: duplicate included changeset id" }
        $file = Join-Path $StateRoot $entry.path
        if (!(Test-Path $file)) { throw "Core-state materialization failed: included changeset is missing: $($entry.path)" }
        $status = (& $Cli db changeset status $file --json | ConvertFrom-Json).result
        if ($LASTEXITCODE -ne 0 -or $status.id -ne $entry.id -or $status.content_sha256 -ne $entry.content_sha256) {
            throw "Core-state materialization failed: included changeset identity changed: $($entry.path)"
        }
        $includedById[$entry.id] = $entry
    }

    if (Test-Path $Changesets) {
        foreach ($file in Get-ChildItem -LiteralPath $Changesets -Filter "*.changeset.jsonl" | Sort-Object FullName) {
            $relative = [System.IO.Path]::GetRelativePath($StateRoot, $file.FullName).Replace('\', '/')
            $status = (& $Cli db changeset status $file.FullName --json | ConvertFrom-Json).result
            if ($LASTEXITCODE -ne 0) { throw "Core-state materialization failed: invalid changeset: $($file.FullName)" }
            if ($includedById.ContainsKey($status.id)) {
                $entry = $includedById[$status.id]
                if ($entry.path -ne $relative -or $entry.content_sha256 -ne $status.content_sha256) {
                    throw "Core-state materialization failed: compacted changeset id or bytes changed: $relative"
                }
            } else {
                Push-Location $StateRoot
                try {
                    & $Cli db changeset apply $relative --json | Out-Null
                    if ($LASTEXITCODE -ne 0) { throw "Core-state materialization failed: changeset replay failed: $relative" }
                } finally {
                    Pop-Location
                }
            }
        }
    }

    $contract = (& $Cli query contract --json | ConvertFrom-Json).result
    if ($contract.database_state -ne "current" -or $contract.database_schema_version -ne $model.snapshot.schema_version) {
        throw "Core-state materialization failed: materialized schema differs from the manifest"
    }
    $stories = (& $Cli query stories --json | ConvertFrom-Json).result.stories
    $ownershipPath = Join-Path $root "docs/stories/epics/E11-symphony-repository-separation/US-089-separation-boundary-and-frozen-baselines/evidence/durable-ownership-map.json"
    $forbidden = (Get-Content -LiteralPath $ownershipPath -Raw | ConvertFrom-Json).records |
        Where-Object { $_.table -eq "story" -and $_.owner -eq "symphony" } | ForEach-Object { $_.identity }
    if ($stories | Where-Object { $forbidden -contains $_.id }) {
        throw "Core-state materialization failed: database contains Symphony-owned stories"
    }
    foreach ($proxy in @("US-093", "US-094", "US-095", "US-096")) {
        if (!($stories | Where-Object { $_.id -eq $proxy -and $_.status -eq "implemented" -and !$_.runnable })) {
            throw "Core-state materialization failed: required core receipt proxy is invalid: $proxy"
        }
    }
    $tools = & $Cli query tools --json | ConvertFrom-Json
    if ($tools | Where-Object { $_.name -in @("impeccable", "web-ui-build", "web-ui-e2e", "web-ui-desktop-smoke") }) {
        throw "Core-state materialization failed: core tool registry contains product-owned providers"
    }
    $openBacklog = & $Cli query backlog --open
    if ($openBacklog -match '(?i)symphony') { throw "Core-state materialization failed: active backlog contains Symphony product work" }

    Move-Item -LiteralPath $candidate -Destination $Database
    Write-Host "Core state materialized: database=$Database snapshot_sha256=$actualHash"
} finally {
    Remove-Item -LiteralPath $temporary -Recurse -Force -ErrorAction SilentlyContinue
}
