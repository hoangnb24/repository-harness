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
& cargo build --quiet --manifest-path (Join-Path $Root "Cargo.toml") -p harness --locked
if (!$?) { throw "failed to build the core maintenance CLI" }
$env:HARNESS_CORE_BINARY = Join-Path $Root "target/debug/harness.exe"

function Invoke-Install([string]$Directory, [string[]]$Mode = @()) {
    $Arguments = @{ Directory = $Directory; Yes = $true }
    foreach ($Name in $Mode) { $Arguments[$Name] = $true }
    & $Installer @Arguments | Out-Null
    if (!$?) { throw "installer failed for $Directory $Mode" }
}

try {
    $Fresh = Join-Path $Temp "fresh"
    Invoke-Install $Fresh
    if (Test-Path (Join-Path $Fresh "scripts/bin/harness-cli.exe")) { throw "default core installed CLI" }
    if (!(Test-Path (Join-Path $Fresh "scripts/bin/harness.exe"))) { throw "default core maintenance CLI missing" }
    if (Test-Path (Join-Path $Fresh "scripts/schema")) { throw "default core installed schemas" }
    if (!(Get-Content -Raw (Join-Path $Fresh ".gitignore")).Contains("scripts/bin/harness.exe")) { throw "default core binary ignore rule missing" }
    if ((Get-Content -Raw (Join-Path $Fresh ".gitignore")).Contains("harness.db")) { throw "default core wrote control-plane ignore rules" }
    if (Test-Path (Join-Path $Fresh "harness.db")) { throw "fresh install initialized local DB" }
    if (!(Test-Path (Join-Path $Fresh ".harness-core/manifest.json"))) { throw "fresh core provenance missing" }
    if (!(Test-Path (Join-Path $Fresh "docs/WORKFLOW.md"))) { throw "fresh workflow missing" }
    if (!(Test-Path (Join-Path $Fresh "docs/plans/active/README.md"))) { throw "fresh active-plan path missing" }
    if (!(Test-Path (Join-Path $Fresh "docs/templates/exec-plan.md"))) { throw "fresh execution-plan template missing" }
    if (!(Test-Path (Join-Path $Fresh ".agents/skills/onboard-repository/SKILL.md"))) { throw "fresh onboarding skill missing" }
    if (!(Test-Path (Join-Path $Fresh ".agents/skills/onboard-repository/scripts/render_patch.py"))) { throw "fresh onboarding renderer missing" }
    if (!(Test-Path (Join-Path $Fresh ".agents/skills/audit-onboarding-proposal/SKILL.md"))) { throw "fresh onboarding audit skill missing" }
    if (!(Test-Path (Join-Path $Fresh ".agents/skills/audit-onboarding-proposal/scripts/validate_evidence_capsule.py"))) { throw "fresh onboarding validator missing" }
    if (!(Get-Content -Raw (Join-Path $Fresh ".agents/skills/onboard-repository/agents/openai.yaml")).Contains("allow_implicit_invocation: false")) { throw "onboarding skill is not explicit-only" }
    if (!(Get-Content -Raw (Join-Path $Fresh ".agents/skills/audit-onboarding-proposal/agents/openai.yaml")).Contains("allow_implicit_invocation: false")) { throw "onboarding audit skill is not explicit-only" }
    if (!(Get-Content -Raw (Join-Path $Fresh "AGENTS.md")).Contains("No control-plane operation is required.")) { throw "fresh default still requires control-plane commands" }
    if ((Get-Content -Raw (Join-Path $Fresh "AGENTS.md")).Contains("Current Upstream Goal")) { throw "fresh default contains upstream repository goal" }

    $Full = Join-Path $Temp "full"
    Invoke-Install $Full @("WithCli")
    if (!(Test-Path (Join-Path $Full "scripts/bin/harness-cli.exe"))) { throw "explicit CLI missing" }
    if (!(Test-Path (Join-Path $Full "scripts/bootstrap-harness.ps1"))) { throw "CLI bootstrap missing" }
    if (!(Test-Path (Join-Path $Full "docs/contracts/harness-orchestration-v1.md"))) { throw "CLI protocol contract missing" }
    if ((Get-ChildItem (Join-Path $Full "scripts/schema") -Filter "*.sql").Count -ne
        (Get-ChildItem (Join-Path $Root "scripts/schema") -Filter "*.sql").Count) { throw "schema count differs" }
    if (!(Get-Content -Raw (Join-Path $Full ".gitignore")).Contains("harness.db")) { throw "CLI ignore rules missing" }

    $Merge = Join-Path $Temp "merge"
    New-Item -ItemType Directory -Force (Join-Path $Merge "docs"), (Join-Path $Merge "scripts/custom"), (Join-Path $Merge "scripts/bin") | Out-Null
    "project agents" | Set-Content (Join-Path $Merge "AGENTS.md")
    "project harness" | Set-Content (Join-Path $Merge "docs/HARNESS.md")
    "keep" | Set-Content (Join-Path $Merge "scripts/custom/keep.txt")
    "existing cli" | Set-Content (Join-Path $Merge "scripts/bin/harness-cli.exe")
    "existing database" | Set-Content (Join-Path $Merge "harness.db")
    Invoke-Install $Merge @("Merge")
    if ((Get-Content -Raw (Join-Path $Merge "AGENTS.md")).Trim() -ne "project agents") { throw "merge replaced AGENTS" }
    if ((Get-Content -Raw (Join-Path $Merge "docs/HARNESS.md")).Trim() -ne "project harness") { throw "merge replaced docs" }
    if (!(Test-Path (Join-Path $Merge "docs/WORKFLOW.md"))) { throw "merge did not fill core payload" }
    if (!(Test-Path (Join-Path $Merge ".agents/skills/onboard-repository/SKILL.md"))) { throw "merge did not fill onboarding skill" }
    if (!(Test-Path (Join-Path $Merge ".agents/skills/audit-onboarding-proposal/SKILL.md"))) { throw "merge did not fill onboarding audit skill" }
    if (Test-Path (Join-Path $Merge "docs/ARCHITECTURE.md")) { throw "core merge installed upstream architecture" }
    if ((Get-Content -Raw (Join-Path $Merge "scripts/bin/harness-cli.exe")).Trim() -ne "existing cli") { throw "core merge changed existing CLI" }
    if ((Get-Content -Raw (Join-Path $Merge "harness.db")).Trim() -ne "existing database") { throw "core merge changed existing database" }
    if (!(Get-Content -Raw (Join-Path $Merge ".gitignore")).Contains("scripts/bin/harness.exe")) { throw "core merge binary ignore rule missing" }
    if ((Get-Content -Raw (Join-Path $Merge ".gitignore")).Contains("harness.db")) { throw "core merge wrote control-plane ignore rules" }

    $Override = Join-Path $Temp "override"
    New-Item -ItemType Directory -Force (Join-Path $Override "docs"), (Join-Path $Override "scripts") | Out-Null
    "old agents" | Set-Content (Join-Path $Override "AGENTS.md")
    "old docs" | Set-Content (Join-Path $Override "docs/private.md")
    "old scripts" | Set-Content (Join-Path $Override "scripts/private.ps1")
    Invoke-Install $Override @("Override")
    $Backup = Get-ChildItem (Join-Path $Override ".harness-backup") -Directory | Select-Object -First 1
    if (!(Test-Path (Join-Path $Backup.FullName "docs/private.md"))) { throw "override docs backup missing" }
    if (Test-Path (Join-Path $Override "docs/private.md")) { throw "override leaked old docs" }
    if ((Get-Content -Raw (Join-Path $Override "scripts/private.ps1")).Trim() -ne "old scripts") { throw "core override changed scripts" }

    $Shim = Join-Path $Temp "shim"
    New-Item -ItemType Directory -Force (Join-Path $Shim "docs"), (Join-Path $Shim "scripts") | Out-Null
    "local rule`n`n<!-- HARNESS:BEGIN -->`nstale`n<!-- HARNESS:END -->" | Set-Content (Join-Path $Shim "AGENTS.md")
    Invoke-Install $Shim @("Merge", "RefreshAgentShim")
    $ShimText = Get-Content -Raw (Join-Path $Shim "AGENTS.md")
    if (!$ShimText.Contains("local rule") -or !$ShimText.Contains("No control-plane operation is required.") -or $ShimText.Contains("stale")) { throw "shim refresh failed" }

    $Dry = Join-Path $Temp "dry"
    & $Installer -Directory $Dry -Yes -DryRun | Out-Null
    if (Test-Path $Dry) { throw "dry-run wrote target" }

    $CliDry = Join-Path $Temp "cli-dry"
    & $Installer -Directory $CliDry -Yes -WithCli -DryRun | Out-Null
    if (Test-Path $CliDry) { throw "CLI dry-run wrote target" }

    $BadAssets = Join-Path $Temp "bad-assets"
    New-Item -ItemType Directory -Force $BadAssets | Out-Null
    Copy-Item $CandidateArtifact (Join-Path $BadAssets $AssetName)
    "bad-checksum" | Set-Content -Encoding ascii (Join-Path $BadAssets "$AssetName.sha256")
    $GoodBaseUrl = $env:HARNESS_CLI_BASE_URL
    $env:HARNESS_CLI_BASE_URL = ([uri](Resolve-Path $BadAssets).Path).AbsoluteUri.TrimEnd("/")
    $Failed = Join-Path $Temp "failed-cli"
    try {
        & $Installer -Directory $Failed -Yes -WithCli | Out-Null
        throw "installer unexpectedly accepted bad CLI checksum"
    } catch {
        if ($_.Exception.Message -eq "installer unexpectedly accepted bad CLI checksum") { throw }
    } finally {
        $env:HARNESS_CLI_BASE_URL = $GoodBaseUrl
    }
    if (!(Test-Path (Join-Path $Failed "AGENTS.md"))) { throw "failed CLI removed usable core" }
    if (!(Test-Path (Join-Path $Failed "scripts/bin/harness.exe"))) { throw "failed optional CLI removed core maintenance CLI" }
    if (Test-Path (Join-Path $Failed "docs/FEATURE_INTAKE.md")) { throw "failed CLI left compatibility docs" }
    if (Test-Path (Join-Path $Failed "scripts/bootstrap-harness.ps1")) { throw "failed CLI left bootstrap" }
    if (!(Get-Content -Raw (Join-Path $Failed ".gitignore")).Contains("scripts/bin/harness.exe")) { throw "failed optional CLI removed core binary ignore rule" }
    if ((Get-Content -Raw (Join-Path $Failed ".gitignore")).Contains("harness.db")) { throw "failed CLI left control-plane ignore rules" }

    if ($InitialArtifact) {
        $InitialArtifact = (Resolve-Path $InitialArtifact).Path
        & (Join-Path $Root "tests/protocol/smoke-v0.1.14-artifact.ps1") -Artifact $InitialArtifact
        if (!$?) { throw "frozen initial protocol smoke failed" }
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
        if (!$UpgradeAgents.Contains("local rule") -or $UpgradeAgents.Contains("stale authority") -or !$UpgradeAgents.Contains("No control-plane operation is required.")) { throw "upgrade did not refresh marked AGENTS authority" }
        if (!(Get-ChildItem (Join-Path $Upgrade ".harness-backup") -Recurse -Filter "AGENTS.md" -File | Select-Object -First 1)) { throw "upgrade AGENTS backup missing" }
        & (Join-Path $Upgrade "scripts/bin/harness-cli.exe") --version | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "upgraded candidate does not execute" }
        $BinaryVersion = (& (Join-Path $Upgrade "scripts/bin/harness-cli.exe") --version).Split()[-1]
        if ($CandidateRef -ne "harness-cli-v0.0.0-candidate" -and $CandidateRef -ne "harness-cli-v$BinaryVersion") {
            throw "candidate tuple mismatch: ref=$CandidateRef binary=$BinaryVersion"
        }
        & (Join-Path $Root "tests/protocol/smoke-native-artifact.ps1") -Artifact (Join-Path $Upgrade "scripts/bin/harness-cli.exe")
        if (!$?) { throw "installed candidate protocol smoke failed" }
        Write-Host "candidate tuple: template_ref=$CandidateRef binary_version=$BinaryVersion binary_sha256=$CandidateHash"
    }

    Write-Host "PowerShell core/CLI profiles, merge, override, shim, rollback, dry-run, and upgrade modes passed"
}
finally {
    Remove-Item Env:HARNESS_CLI_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:HARNESS_CLI_PLATFORM -ErrorAction SilentlyContinue
    Remove-Item Env:HARNESS_CORE_BINARY -ErrorAction SilentlyContinue
    Remove-Item Env:HARNESS_SOURCE_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $Temp -ErrorAction SilentlyContinue
}
