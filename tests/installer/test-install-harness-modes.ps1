param(
    [Parameter(Mandatory = $true)][string]$CandidateArtifact,
    [string]$InitialArtifact,
    [string]$CandidateRef = "harness-cli-v0.0.0-candidate"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$Installer = Join-Path $Root "scripts/install-harness.ps1"
$CandidateArtifact = (Resolve-Path $CandidateArtifact).Path
$Temp = Join-Path ([System.IO.Path]::GetTempPath()) ("harness-installer-modes-" + [guid]::NewGuid())
$Assets = Join-Path $Temp "assets"
$AssetName = "harness-cli-windows-x64.exe"
New-Item -ItemType Directory -Force $Assets | Out-Null
Copy-Item $CandidateArtifact (Join-Path $Assets $AssetName)
$CandidateHash = (Get-FileHash -Algorithm SHA256 $CandidateArtifact).Hash.ToLowerInvariant()
"$CandidateHash  $AssetName" | Set-Content -Encoding ascii (Join-Path $Assets "$AssetName.sha256")
$env:HARNESS_CLI_BASE_URL = ([uri](Resolve-Path $Assets).Path).AbsoluteUri.TrimEnd("/")
$env:HARNESS_CLI_PLATFORM = "windows-x64"

function Invoke-Install([string]$Directory, [string[]]$Mode = @()) {
    $Arguments = @{ Directory = $Directory; Yes = $true }
    foreach ($Name in $Mode) { $Arguments[$Name] = $true }
    & $Installer @Arguments | Out-Null
    if (!$?) { throw "installer failed for $Directory $Mode" }
}

try {
    $Fresh = Join-Path $Temp "fresh"
    Invoke-Install $Fresh
    if (!(Test-Path (Join-Path $Fresh "scripts/bin/harness-cli.exe"))) { throw "fresh CLI missing" }
    if (Test-Path (Join-Path $Fresh "harness.db")) { throw "fresh install initialized local DB" }
    if ((Get-ChildItem (Join-Path $Fresh "scripts/schema") -Filter "*.sql").Count -ne
        (Get-ChildItem (Join-Path $Root "scripts/schema") -Filter "*.sql").Count) { throw "schema count differs" }

    $Merge = Join-Path $Temp "merge"
    New-Item -ItemType Directory -Force (Join-Path $Merge "docs"), (Join-Path $Merge "scripts/custom") | Out-Null
    "project agents" | Set-Content (Join-Path $Merge "AGENTS.md")
    "project harness" | Set-Content (Join-Path $Merge "docs/HARNESS.md")
    "keep" | Set-Content (Join-Path $Merge "scripts/custom/keep.txt")
    Invoke-Install $Merge @("Merge")
    if ((Get-Content -Raw (Join-Path $Merge "AGENTS.md")).Trim() -ne "project agents") { throw "merge replaced AGENTS" }
    if ((Get-Content -Raw (Join-Path $Merge "docs/HARNESS.md")).Trim() -ne "project harness") { throw "merge replaced docs" }
    if (!(Test-Path (Join-Path $Merge "docs/ARCHITECTURE.md"))) { throw "merge did not fill missing payload" }

    $Override = Join-Path $Temp "override"
    New-Item -ItemType Directory -Force (Join-Path $Override "docs"), (Join-Path $Override "scripts") | Out-Null
    "old agents" | Set-Content (Join-Path $Override "AGENTS.md")
    "old docs" | Set-Content (Join-Path $Override "docs/private.md")
    "old scripts" | Set-Content (Join-Path $Override "scripts/private.ps1")
    Invoke-Install $Override @("Override")
    $Backup = Get-ChildItem (Join-Path $Override ".harness-backup") -Directory | Select-Object -First 1
    if (!(Test-Path (Join-Path $Backup.FullName "docs/private.md"))) { throw "override docs backup missing" }
    if (Test-Path (Join-Path $Override "docs/private.md")) { throw "override leaked old docs" }

    $Shim = Join-Path $Temp "shim"
    New-Item -ItemType Directory -Force (Join-Path $Shim "docs"), (Join-Path $Shim "scripts") | Out-Null
    "local rule`n`n<!-- HARNESS:BEGIN -->`nstale`n<!-- HARNESS:END -->" | Set-Content (Join-Path $Shim "AGENTS.md")
    Invoke-Install $Shim @("Merge", "RefreshAgentShim")
    $ShimText = Get-Content -Raw (Join-Path $Shim "AGENTS.md")
    if (!$ShimText.Contains("local rule") -or !$ShimText.Contains("query matrix --active --summary") -or $ShimText.Contains("stale")) { throw "shim refresh failed" }

    $Dry = Join-Path $Temp "dry"
    & $Installer -Directory $Dry -Yes -DryRun | Out-Null
    if (Test-Path $Dry) { throw "dry-run wrote target" }

    if ($InitialArtifact) {
        $InitialArtifact = (Resolve-Path $InitialArtifact).Path
        $Upgrade = Join-Path $Temp "upgrade"
        New-Item -ItemType Directory -Force (Join-Path $Upgrade "scripts/bin") | Out-Null
        Copy-Item $InitialArtifact (Join-Path $Upgrade "scripts/bin/harness-cli.exe")
        "consumer-owned" | Set-Content (Join-Path $Upgrade "KEEP.txt")
        "local rule`n`n<!-- HARNESS:BEGIN -->`nstale authority`n<!-- HARNESS:END -->" | Set-Content (Join-Path $Upgrade "AGENTS.md")
        $env:HARNESS_SOURCE_BASE_URL = ([uri]$Root).AbsoluteUri.TrimEnd("/")
        & $Installer -Directory $Upgrade -Yes -Merge -UpgradeCli -Ref $CandidateRef | Out-Null
        if ((Get-FileHash -Algorithm SHA256 (Join-Path $Upgrade "scripts/bin/harness-cli.exe")).Hash.ToLowerInvariant() -ne $CandidateHash) { throw "candidate upgrade hash differs" }
        if ((Get-Content -Raw (Join-Path $Upgrade "KEEP.txt")).Trim() -ne "consumer-owned") { throw "upgrade changed consumer file" }
        $UpgradeAgents = Get-Content -Raw (Join-Path $Upgrade "AGENTS.md")
        if (!$UpgradeAgents.Contains("local rule") -or $UpgradeAgents.Contains("stale authority") -or !$UpgradeAgents.Contains("query matrix --active --summary")) { throw "upgrade did not refresh marked AGENTS authority" }
        if (!(Get-ChildItem (Join-Path $Upgrade ".harness-backup") -Recurse -Filter "AGENTS.md" -File | Select-Object -First 1)) { throw "upgrade AGENTS backup missing" }
        & (Join-Path $Upgrade "scripts/bin/harness-cli.exe") --version | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "upgraded candidate does not execute" }
        $BinaryVersion = (& (Join-Path $Upgrade "scripts/bin/harness-cli.exe") --version).Split()[-1]
        if ($CandidateRef -ne "harness-cli-v0.0.0-candidate" -and $CandidateRef -ne "harness-cli-v$BinaryVersion") {
            throw "candidate tuple mismatch: ref=$CandidateRef binary=$BinaryVersion"
        }
        Write-Host "candidate tuple: template_ref=$CandidateRef binary_version=$BinaryVersion binary_sha256=$CandidateHash"
    }

    Write-Host "PowerShell installer fresh, merge, override, shim-refresh, dry-run, and candidate upgrade modes passed"
}
finally {
    Remove-Item Env:HARNESS_CLI_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:HARNESS_CLI_PLATFORM -ErrorAction SilentlyContinue
    Remove-Item Env:HARNESS_SOURCE_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $Temp -ErrorAction SilentlyContinue
}
