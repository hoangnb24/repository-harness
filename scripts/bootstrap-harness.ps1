param(
    [string]$Database = $env:HARNESS_DB_PATH,
    [string]$Cli = $env:HARNESS_CLI
)

$ErrorActionPreference = "Stop"
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
if ([string]::IsNullOrWhiteSpace($Database)) {
    $Database = Join-Path $root "harness.db"
}
if ([string]::IsNullOrWhiteSpace($Cli)) {
    $Cli = Join-Path $root "scripts/bin/harness-cli.exe"
}
$Database = [System.IO.Path]::GetFullPath($Database)
$Cli = [System.IO.Path]::GetFullPath($Cli)
$defaultDatabase = [System.IO.Path]::GetFullPath((Join-Path $root "harness.db"))
$sourceCheckout = (Test-Path (Join-Path $root "Cargo.toml")) -and
    (Test-Path (Join-Path $root "crates/harness-cli/Cargo.toml"))

if ($sourceCheckout -and $Database -eq $defaultDatabase -and !(Test-Path $Database) -and
    (!(Test-Path (Join-Path $root ".harness/core-state/manifest.json")) -or
     !(Test-Path (Join-Path $root ".harness/core-state/harness.db")))) {
    throw "Harness bootstrap failed: authoritative core state is unavailable; tracked verified core state is missing"
}

if ($sourceCheckout) {
    if (!(Get-Command cargo -ErrorAction SilentlyContinue)) {
        throw "Harness bootstrap failed: cargo is required in a Harness CLI source checkout"
    }
    & cargo build --quiet --manifest-path (Join-Path $root "Cargo.toml") -p harness-cli --locked
    if ($LASTEXITCODE -ne 0) { throw "Harness bootstrap failed: cargo build failed" }
    $builtCli = Join-Path $root "target/debug/harness-cli.exe"
    if ([System.IO.Path]::GetFullPath($builtCli) -ne [System.IO.Path]::GetFullPath($Cli)) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Cli) | Out-Null
        Copy-Item -LiteralPath $builtCli -Destination $Cli -Force
    }
} elseif (!(Test-Path $Cli)) {
    throw "Harness bootstrap failed: Harness CLI is missing; install Harness again from its pinned release"
}

$releaseTagFile = Join-Path $root "scripts/harness-cli-release-tag"
if (!(Test-Path $releaseTagFile)) {
    throw "Harness bootstrap failed: pinned release file is missing: $releaseTagFile"
}
$releaseTag = (Get-Content -LiteralPath $releaseTagFile | Where-Object {
    $_ -match "\S" -and $_ -notmatch "^\s*#"
} | Select-Object -First 1).Trim()
$actualVersion = (& $Cli --version).Split()[-1]
$expectedVersion = $releaseTag -replace '^harness-cli-v', ''
if (!$releaseTag.StartsWith("harness-cli-v") -or $actualVersion -ne $expectedVersion) {
    throw "Harness bootstrap failed: CLI version $actualVersion does not match pinned release $releaseTag"
}

if ($sourceCheckout -and $Database -eq $defaultDatabase -and !(Test-Path $Database)) {
    & (Join-Path $root "scripts/materialize-core-state.ps1") -Database $Database -Cli $Cli
    if ($LASTEXITCODE -ne 0) { throw "Harness bootstrap failed: tracked core-state materialization failed" }
}

function Get-Contract {
    $env:HARNESS_REPO_ROOT = $root
    $env:HARNESS_DB_PATH = $Database
    $json = & $Cli query contract --json
    if ($LASTEXITCODE -ne 0) { throw "Harness bootstrap failed: query contract failed" }
    return ($json | ConvertFrom-Json).result
}

$contract = Get-Contract
switch ($contract.database_state) {
    "missing" { & $Cli init | Out-Null }
    "needs_migration" { & $Cli migrate | Out-Null }
    "current" { }
    "unsupported" { throw "Harness bootstrap failed: database schema is outside the CLI's supported range" }
    default { throw "Harness bootstrap failed: query contract returned an unknown database state" }
}
if ($LASTEXITCODE -ne 0) { throw "Harness bootstrap failed: database initialization or migration failed" }

$contract = Get-Contract
if ($contract.database_state -ne "current") {
    throw "Harness bootstrap failed: database did not reach current schema"
}
if ($sourceCheckout -and $Database -eq $defaultDatabase) {
    $stories = (& $Cli query stories --json | ConvertFrom-Json).result.stories
    $ownershipPath = Join-Path $root "docs/stories/epics/E11-symphony-repository-separation/US-089-separation-boundary-and-frozen-baselines/evidence/durable-ownership-map.json"
    $forbidden = (Get-Content -LiteralPath $ownershipPath -Raw | ConvertFrom-Json).records |
        Where-Object { $_.table -eq "story" -and $_.owner -eq "symphony" } |
        ForEach-Object { $_.identity }
    $leaked = $stories | Where-Object { $forbidden -contains $_.id }
    if ($leaked) {
        throw "Harness bootstrap failed: core database contains Symphony-owned story state: $(($leaked.id | Sort-Object) -join ', ')"
    }
    foreach ($proxy in @("US-093", "US-094", "US-095", "US-096")) {
        if (!($stories | Where-Object { $_.id -eq $proxy -and $_.status -eq "implemented" -and !$_.runnable })) {
            throw "Harness bootstrap failed: required core receipt proxy is missing or invalid: $proxy"
        }
    }
    $foreignTools = & $Cli query tools --json | ConvertFrom-Json | Where-Object {
        $_.name -in @("impeccable", "web-ui-build", "web-ui-e2e", "web-ui-desktop-smoke")
    }
    if ($foreignTools) {
        throw "Harness bootstrap failed: core tool registry contains product-owned providers: $(($foreignTools.name | Sort-Object) -join ', ')"
    }
}
Write-Host "Harness ready: cli=$Cli database=$Database"
