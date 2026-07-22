param(
    [Alias("d")]
    [string]$Directory = $env:HARNESS_TARGET_DIR,
    [Alias("y")]
    [switch]$Yes,
    [switch]$Merge,
    [switch]$WithCli,
    [switch]$UpgradeCli,
    [string]$Ref,
    [switch]$RefreshAgentShim,
    [switch]$Override,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host $Message
}

function Fail([string]$Message) {
    throw "Error: $Message"
}

function Resolve-TargetPath([string]$PathValue) {
    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        $PathValue = (Get-Location).Path
    }

    $expanded = [Environment]::ExpandEnvironmentVariables($PathValue)
    if ($expanded.StartsWith("~")) {
        $expanded = Join-Path $HOME $expanded.Substring(1).TrimStart("\", "/")
    }
    if ([System.IO.Path]::IsPathRooted($expanded)) {
        return [System.IO.Path]::GetFullPath($expanded)
    }
    return [System.IO.Path]::GetFullPath((Join-Path (Get-Location).Path $expanded))
}

function Get-SourceMode {
    if ($PSScriptRoot) {
        $candidate = Split-Path -Parent $PSScriptRoot
        if ((Test-Path (Join-Path $candidate "AGENTS.md")) -and (Test-Path (Join-Path $candidate "docs/HARNESS.md"))) {
            return @{ Mode = "local"; Root = $candidate }
        }
    }
    return @{ Mode = "remote"; Root = "" }
}

function Read-RemoteText([string]$Url) {
    if ($Url.StartsWith("file://")) {
        return Get-Content -LiteralPath ([uri]$Url).LocalPath -Raw
    }
    return (Invoke-WebRequest -UseBasicParsing -Uri $Url).Content
}

function Write-SourceFile([string]$Relative, [string]$Target) {
    if ($Relative -eq "AGENTS.md") {
        $block = (Read-SourceText "scripts/agent-harness-block.md").TrimEnd("`r", "`n")
        Set-Content -LiteralPath $Target -Value ("# Agent Instructions`n`n" + $block + "`n") -NoNewline
        return
    }

    if ($script:Source.Mode -eq "local") {
        $source = Join-Path $script:Source.Root $Relative
        if (!(Test-Path $source)) {
            Fail "Source file missing: $source"
        }
        Copy-Item -LiteralPath $source -Destination $Target -Force
        return
    }

    $url = "$script:SourceBaseUrl/$($Relative -replace '\\','/')"
    if ($url.StartsWith("file://")) {
        Copy-Item -LiteralPath ([uri]$url).LocalPath -Destination $Target -Force
    } else {
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $Target
    }
}

function Read-SourceText([string]$Relative) {
    if ($script:Source.Mode -eq "local") {
        $source = Join-Path $script:Source.Root $Relative
        if (!(Test-Path $source)) {
            Fail "Source file missing: $source"
        }
        return Get-Content -LiteralPath $source -Raw
    }

    $url = "$script:SourceBaseUrl/$($Relative -replace '\\','/')"
    return Read-RemoteText $url
}

function Read-PayloadManifest([string]$Manifest) {
    if ($script:Source.Mode -eq "local") {
        $path = Join-Path $script:Source.Root $Manifest
        if (!(Test-Path $path)) {
            Fail "Payload manifest missing: $path"
        }
        return Get-Content -LiteralPath $path
    }

    $url = "$script:SourceBaseUrl/$Manifest"
    try {
        return ((Read-RemoteText $url) -split "\r?\n")
    } catch {
        Fail "Could not download $url"
    }
}

function Get-PayloadFiles([string]$Manifest) {
    foreach ($line in (Read-PayloadManifest $Manifest)) {
        $relative = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($relative) -or $relative.StartsWith("#")) {
            continue
        }
        $relative
    }
}

function Get-SchemaFiles {
    if ($script:Source.Mode -eq "local") {
        $schemaRoot = Join-Path $script:Source.Root $script:SchemaDir
        if (!(Test-Path $schemaRoot)) {
            Fail "Schema directory missing: $schemaRoot"
        }
        return Get-ChildItem -LiteralPath $schemaRoot -Filter "*.sql" -File |
            Sort-Object Name |
            ForEach-Object { "$script:SchemaDir/$($_.Name)" }
    }

    if ($script:SourceBaseUrl.StartsWith("file://")) {
        $sourceRoot = ([uri]$script:SourceBaseUrl).LocalPath
        $schemaRoot = Join-Path $sourceRoot $script:SchemaDir
        if (!(Test-Path $schemaRoot)) {
            Fail "Schema directory missing: $schemaRoot"
        }
        return Get-ChildItem -LiteralPath $schemaRoot -Filter "*.sql" -File |
            Sort-Object Name |
            ForEach-Object { "$script:SchemaDir/$($_.Name)" }
    }

    if ($script:SourceBaseUrl.StartsWith("https://raw.githubusercontent.com/")) {
        $uri = [uri]$script:SourceBaseUrl
        $parts = $uri.AbsolutePath.Trim("/").Split("/")
        if ($parts.Count -lt 3) {
            Fail "Cannot infer GitHub repository from $script:SourceBaseUrl"
        }
        $owner = $parts[0]
        $repo = $parts[1]
        $ref = $parts[2]
        $apiUrl = "https://api.github.com/repos/$owner/$repo/git/trees/$ref`?recursive=1"
        try {
            $tree = Read-RemoteText $apiUrl | ConvertFrom-Json
        } catch {
            Fail "Could not download $apiUrl"
        }
        return $tree.tree |
            Where-Object { $_.type -eq "blob" -and $_.path -like "$script:SchemaDir/*.sql" } |
            Sort-Object path |
            ForEach-Object { $_.path }
    }

    Fail "Cannot discover remote schema files from $script:SourceBaseUrl. Use a local source, file:// source, or raw.githubusercontent.com source."
}

function Merge-Gitignore([string]$Target) {
    $rules = @(
        "# Harness durable layer",
        "harness.db",
        "harness.db-wal",
        "harness.db-shm",
        "scripts/bin/harness-cli",
        "scripts/bin/harness-cli.exe"
    )

    $existing = if (Test-Path $Target) { Get-Content -LiteralPath $Target } else { @() }
    $missing = $rules | Where-Object { $existing -notcontains $_ }
    if ($missing.Count -eq 0) {
        Write-Step "skip     .gitignore (harness rules already present)"
        $script:Skipped++
        return
    }

    if ($DryRun) {
        Write-Step "update   .gitignore (append harness rules)"
    } else {
        $prefix = if ((Test-Path $Target) -and ((Get-Item $Target).Length -gt 0)) { "`n" } else { "" }
        Add-Content -LiteralPath $Target -Value ($prefix + (($missing -join "`n") + "`n")) -NoNewline
        Write-Step "updated  .gitignore (appended harness rules)"
    }
    $script:Updated++
}

function Copy-HarnessFile([string]$Relative) {
    $target = Join-Path $script:TargetDir $Relative

    if ($Relative -eq ".gitignore" -and (Test-Path $target) -and !$Force) {
        Merge-Gitignore $target
        return
    }

    if (Test-Path $target) {
        if ($script:ConflictAction -eq "merge") {
            Write-Step "skip     $Relative (merge keeps existing file)"
            $script:Skipped++
        } elseif ($Force) {
            if ($DryRun) {
                Write-Step "overwrite $Relative (backup first)"
            } else {
                $backup = Join-Path $script:BackupDir $Relative
                New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
                Copy-Item -LiteralPath $target -Destination $backup -Force
                Write-SourceFile $Relative $target
                Write-Step "updated  $Relative (backup: $($backup.Substring($script:TargetDir.Length + 1)))"
            }
            $script:Updated++
        } else {
            Write-Step "skip     $Relative (already exists)"
            $script:Skipped++
        }
        return
    }

    if ($DryRun) {
        Write-Step "create   $Relative"
    } else {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        Write-SourceFile $Relative $target
        Write-Step "created  $Relative"
    }
    $script:Created++
}

function Get-AgentShimBlock {
    return (Read-SourceText "scripts/agent-harness-block.md").TrimEnd("`r", "`n")
}

function Assert-HarnessMarkers([string]$Content, [string]$Label) {
    $begin = [regex]::Matches($Content, '<!-- HARNESS:BEGIN -->')
    $end = [regex]::Matches($Content, '<!-- HARNESS:END -->')
    if ($begin.Count -eq 0 -and $end.Count -eq 0) {
        return
    }
    if ($begin.Count -ne 1 -or $end.Count -ne 1) {
        Fail "$Label must contain exactly one complete Harness marker pair"
    }
    if ($begin[0].Index -ge $end[0].Index) {
        Fail "$Label Harness markers are out of order"
    }
}

function Refresh-AgentShimFile {
    if (!$RefreshAgentShim) {
        return
    }
    $target = Join-Path $script:TargetDir "AGENTS.md"
    if (!(Test-Path $target)) {
        return
    }

    $content = Get-Content -LiteralPath $target -Raw
    Assert-HarnessMarkers $content "AGENTS.md"

    if ($DryRun) {
        Write-Step "refresh  AGENTS.md (replace marked Harness block, backup first)"
        $script:Updated++
        return
    }

    New-Item -ItemType Directory -Force -Path $script:BackupDir | Out-Null
    $backup = Join-Path $script:BackupDir "AGENTS.md"
    if (!(Test-Path $backup)) {
        Copy-Item -LiteralPath $target -Destination $backup
    }

    $block = Get-AgentShimBlock
    if ($content -match "(?s)<!-- HARNESS:BEGIN -->.*?<!-- HARNESS:END -->") {
        $content = [regex]::Replace($content, "(?s)<!-- HARNESS:BEGIN -->.*?<!-- HARNESS:END -->", [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $block })
    } else {
        $content = $content.TrimEnd() + "`n`n" + $block + "`n"
    }
    Set-Content -LiteralPath $target -Value $content -NoNewline
    Write-Step "updated  AGENTS.md (refreshed Harness block; backup: $($backup.Substring($script:TargetDir.Length + 1)))"
    $script:Updated++
}

function Read-CliReleaseTag {
    $relative = "scripts/harness-cli-release-tag"
    if ($script:Source.Mode -eq "local") {
        $path = Join-Path $script:Source.Root $relative
        if (Test-Path $path) {
            return ((Get-Content -LiteralPath $path | Where-Object { $_ -match "\S" -and $_ -notmatch "^\s*#" } | Select-Object -First 1) -as [string]).Trim()
        }
        return ""
    }

    try {
        $text = Read-RemoteText "$script:SourceBaseUrl/$relative"
        return (($text -split "`n" | Where-Object { $_ -match "\S" -and $_ -notmatch "^\s*#" } | Select-Object -First 1) -as [string]).Trim()
    } catch {
        return ""
    }
}

function Get-DefaultCliBaseUrl {
    $tag = $env:HARNESS_CLI_RELEASE_TAG
    if ([string]::IsNullOrWhiteSpace($tag)) {
        $tag = Read-CliReleaseTag
    }
    if (![string]::IsNullOrWhiteSpace($tag) -and $tag -ne "latest") {
        return "https://github.com/hoangnb24/repository-harness/releases/download/$tag"
    }
    return "https://github.com/hoangnb24/repository-harness/releases/latest/download"
}

function Get-HarnessReleaseTag {
    if ($env:HARNESS_CORE_RELEASE_TAG) { return $env:HARNESS_CORE_RELEASE_TAG.Trim() }
    if ($script:Source.Mode -eq "local") {
        $path = Join-Path $script:Source.Root "scripts/harness-release-tag"
        if (!(Test-Path $path)) { Fail "Harness core release tag is missing: $path" }
        return ((Get-Content -LiteralPath $path | Where-Object { $_ -match "\S" -and $_ -notmatch "^\s*#" } | Select-Object -First 1) -as [string]).Trim()
    }
    try {
        $text = Read-RemoteText "$script:CoreSourceBaseUrl/scripts/harness-release-tag"
        return (($text -split "`n" | Where-Object { $_ -match "\S" -and $_ -notmatch "^\s*#" } | Select-Object -First 1) -as [string]).Trim()
    } catch {
        Fail "Harness core release tag is missing"
    }
}

function Merge-CoreGitignore([string]$Target) {
    $rules = @("# Harness core maintenance binary", "scripts/bin/harness", "scripts/bin/harness.exe")
    $existing = if (Test-Path $Target) { Get-Content -LiteralPath $Target } else { @() }
    $missing = @($rules | Where-Object { $existing -notcontains $_ })
    if ($missing.Count -eq 0) {
        Write-Step "skip     .gitignore (Harness core binary rules already present)"
        return
    }
    if ($DryRun) {
        Write-Step "update   .gitignore (append Harness core binary rules)"
        return
    }
    $prefix = if ((Test-Path $Target) -and ((Get-Item $Target).Length -gt 0)) { "`n" } else { "" }
    Add-Content -LiteralPath $Target -Value ($prefix + (($missing -join "`n") + "`n")) -NoNewline
    Write-Step "updated  .gitignore (appended Harness core binary rules)"
}

function Assert-NotReparsePoint([string]$Path, [string]$Label) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if ($null -ne $item -and (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)) {
        Fail "refusing symlink or reparse point for $Label"
    }
}

function Install-HarnessCore {
    $platform = if ($env:HARNESS_CORE_CLI_PLATFORM) { $env:HARNESS_CORE_CLI_PLATFORM } else { "windows-x64" }
    if ($platform -ne "windows-x64") { Fail "Unsupported Windows Harness core platform: $platform" }
    $stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("harness-core-" + [guid]::NewGuid().ToString("N"))
    $staged = Join-Path $stageRoot "harness.exe"
    $command = if (Test-Path (Join-Path $script:TargetDir ".harness-core/manifest.json")) { "update" } else { "install" }
    $pendingVersion = $null
    $sessionPath = Join-Path $script:TargetDir ".harness-core/update/session.json"
    if ($command -eq "update" -and (Test-Path $sessionPath)) {
        $pendingVersion = (Get-Content -LiteralPath $sessionPath -Raw | ConvertFrom-Json).to_version
        if ([string]::IsNullOrWhiteSpace($pendingVersion)) { Fail "could not read pending Harness update version" }
    }
    New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null
    try {
        if ($env:HARNESS_CORE_BINARY) {
            if (!(Test-Path $env:HARNESS_CORE_BINARY)) { Fail "HARNESS_CORE_BINARY does not exist: $env:HARNESS_CORE_BINARY" }
            Copy-Item -LiteralPath $env:HARNESS_CORE_BINARY -Destination $staged
        } elseif ($script:Source.Mode -eq "local") {
            & cargo build --quiet --manifest-path (Join-Path $script:Source.Root "Cargo.toml") -p harness --locked
            if ($LASTEXITCODE -ne 0) { Fail "could not build the local Rust harness CLI" }
            Copy-Item -LiteralPath (Join-Path $script:Source.Root "target/debug/harness.exe") -Destination $staged
        } else {
            $releaseTag = if ($pendingVersion) { "harness-v$pendingVersion" } else { Get-HarnessReleaseTag }
            if ($releaseTag -notmatch '^harness-v[0-9]+\.[0-9]+\.[0-9]+(?:[-.][A-Za-z0-9]+)*$') { Fail "invalid Harness core release tag: $releaseTag" }
            $baseUrl = if ($env:HARNESS_CORE_CLI_BASE_URL) { $env:HARNESS_CORE_CLI_BASE_URL.TrimEnd("/") } else { "https://github.com/hoangnb24/repository-harness/releases/download/$releaseTag" }
            $binaryUrl = "$baseUrl/harness-windows-x64.exe"
            $checksumUrl = "$binaryUrl.sha256"
            $checksum = "$staged.sha256"
            if ($binaryUrl.StartsWith("file://")) {
                Copy-Item -LiteralPath ([uri]$binaryUrl).LocalPath -Destination $staged
                Copy-Item -LiteralPath ([uri]$checksumUrl).LocalPath -Destination $checksum
            } else {
                Invoke-WebRequest -UseBasicParsing -Uri $binaryUrl -OutFile $staged
                Invoke-WebRequest -UseBasicParsing -Uri $checksumUrl -OutFile $checksum
            }
            $expected = ((Get-Content -LiteralPath $checksum -Raw) -split "\s+")[0].ToLowerInvariant()
            $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $staged).Hash.ToLowerInvariant()
            if ([string]::IsNullOrWhiteSpace($expected) -or $expected -ne $actual) { Fail "Checksum mismatch for harness-windows-x64.exe: expected $expected, got $actual" }
            $reportedVersion = ((& $staged --version) -split "\s+")[-1]
            if ($LASTEXITCODE -ne 0 -or $reportedVersion -ne $releaseTag.Substring(9)) {
                Fail "Harness core release identity mismatch: tag=$($releaseTag.Substring(9)), binary=$reportedVersion"
            }
        }

        $runner = $staged
        $arguments = @($command, "--directory", $script:TargetDir)
        if ($command -eq "update") { $arguments += "--candidate" }
        if ($pendingVersion) { $arguments += "--continue" }
        if ($DryRun) { $arguments += "--dry-run" }
        $target = $null
        $targetTemp = $null
        if (!$DryRun) {
            $target = Join-Path $script:TargetDir "scripts/bin/harness.exe"
            Assert-NotReparsePoint (Join-Path $script:TargetDir "scripts") "repository scripts directory"
            Assert-NotReparsePoint (Join-Path $script:TargetDir "scripts/bin") "repository scripts/bin directory"
            Assert-NotReparsePoint $target "repository Harness executable"
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
            $targetTemp = Join-Path (Split-Path -Parent $target) (".harness." + [guid]::NewGuid().ToString("N") + ".tmp")
            Copy-Item -LiteralPath $staged -Destination $targetTemp
            if (Test-Path $target) {
                $backup = Join-Path $script:BackupDir "scripts/bin/harness.exe"
                New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
                Copy-Item -LiteralPath $target -Destination $backup -Force
            }
        }
        & $runner @arguments
        $commandStatus = $LASTEXITCODE
        if ($commandStatus -eq 2 -and !$DryRun) {
            $retained = Join-Path $script:TargetDir ".harness-core/update-candidate/harness.exe"
            Assert-NotReparsePoint (Join-Path $script:TargetDir ".harness-core") ".harness-core"
            Assert-NotReparsePoint (Join-Path $script:TargetDir ".harness-core/update-candidate") "retained candidate directory"
            Assert-NotReparsePoint $retained "retained update candidate"
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $retained) | Out-Null
            Copy-Item -LiteralPath $staged -Destination $retained -Force
        }
        if ($commandStatus -eq 0 -and !$DryRun) {
            if (Test-Path $target) {
                [System.IO.File]::Replace($targetTemp, $target, $null)
            } else {
                Move-Item -LiteralPath $targetTemp -Destination $target
            }
            Remove-Item -LiteralPath (Join-Path $script:TargetDir ".harness-core/update-candidate") -Recurse -Force -ErrorAction SilentlyContinue
            Merge-CoreGitignore (Join-Path $script:TargetDir ".gitignore")
            Write-Step "installed scripts/bin/harness.exe ($platform)"
        } elseif ($targetTemp) {
            Remove-Item -LiteralPath $targetTemp -Force -ErrorAction SilentlyContinue
        }
        if ($commandStatus -eq 2) { Fail "Harness core update needs resolution; edit .harness-core/update/resolved/, then rerun this installer or harness update --continue" }
        if ($commandStatus -ne 0) { Fail "harness $command failed with exit code $commandStatus" }
    } finally {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Initialize-CliIdentity {
    $script:CliPlatform = if ($env:HARNESS_CLI_PLATFORM) { $env:HARNESS_CLI_PLATFORM } else { "windows-x64" }
    if ($script:CliPlatform -ne "windows-x64") {
        Fail "Unsupported Windows Harness CLI platform: $script:CliPlatform"
    }
    $script:CliBinaryName = "harness-cli-windows-x64.exe"
    $script:CliTargetRelative = "scripts/bin/harness-cli.exe"
}

function Test-PreserveCliBinary {
    $target = Join-Path $script:TargetDir $script:CliTargetRelative
    return (Test-Path $target) -and $script:ConflictAction -eq "merge" -and !$Force -and !$UpgradeCli
}

function Write-CliBinaryPlan {
    $target = Join-Path $script:TargetDir $script:CliTargetRelative
    if (Test-PreserveCliBinary) {
        Write-Step "skip     scripts/bin/harness-cli.exe (merge keeps existing file)"
        $script:Skipped++
        return
    }
    Write-Step "download $script:CliBinaryName -> scripts/bin/harness-cli.exe"
    Write-Step "verify   $script:CliBinaryName.sha256"
    if (Test-Path $target) { $script:Updated++ } else { $script:Created++ }
}

function Stage-HarnessCliBinary([string]$StageRoot) {
    if (Test-PreserveCliBinary) { return }

    $binaryUrl = "$script:CliBaseUrl/$script:CliBinaryName"
    $checksumUrl = "$binaryUrl.sha256"
    $binaryTmp = Join-Path $StageRoot ".binary/$script:CliBinaryName"
    $checksumTmp = "$binaryTmp.sha256"
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $binaryTmp) | Out-Null

    if ($binaryUrl.StartsWith("file://")) {
        Copy-Item -LiteralPath ([uri]$binaryUrl).LocalPath -Destination $binaryTmp
        Copy-Item -LiteralPath ([uri]$checksumUrl).LocalPath -Destination $checksumTmp
    } else {
        Invoke-WebRequest -UseBasicParsing -Uri $binaryUrl -OutFile $binaryTmp
        Invoke-WebRequest -UseBasicParsing -Uri $checksumUrl -OutFile $checksumTmp
    }

    $expected = ((Get-Content -LiteralPath $checksumTmp -Raw) -split "\s+")[0].ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($expected)) {
        Fail "Checksum file is empty: $checksumUrl"
    }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $binaryTmp).Hash.ToLowerInvariant()
    if ($actual -ne $expected) {
        Fail "Checksum mismatch for $script:CliBinaryName`: expected $expected, got $actual"
    }
}

function Install-StagedHarnessCliBinary([string]$StageRoot) {
    $target = Join-Path $script:TargetDir $script:CliTargetRelative
    if (Test-PreserveCliBinary) {
        Write-Step "skip     scripts/bin/harness-cli.exe (merge keeps existing file)"
        $script:Skipped++
        return
    }

    $binaryTmp = Join-Path $StageRoot ".binary/$script:CliBinaryName"
    $targetDir = Split-Path -Parent $target
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

    if (Test-Path $target) {
        if ($Force -or $UpgradeCli) {
            $backup = Join-Path $script:BackupDir $script:CliTargetRelative
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
            Copy-Item -LiteralPath $target -Destination $backup -Force
        }
        $script:Updated++
        Write-Step "updated  scripts/bin/harness-cli.exe"
        $replacementBackup = Join-Path $StageRoot ".binary/replaced-harness-cli.exe"
        [System.IO.File]::Replace($binaryTmp, $target, $replacementBackup)
    } else {
        $script:Created++
        Write-Step "created  scripts/bin/harness-cli.exe"
        Move-Item -LiteralPath $binaryTmp -Destination $target
    }
    Write-Step "verified scripts/bin/harness-cli.exe ($script:CliPlatform)"
}

function Get-CliBundleFiles {
    $files = @()
    $files += Get-PayloadFiles $script:CliPayloadManifest
    $schemas = @(Get-SchemaFiles)
    if ($schemas.Count -eq 0) {
        Fail "No schema migrations found in $script:SchemaDir"
    }
    $files += $schemas
    return @($files | Select-Object -Unique)
}

function Save-CliBundleState([string[]]$Files, [string]$StageRoot) {
    $state = @()
    $rollbackRoot = Join-Path $StageRoot ".rollback"
    $targets = @($Files) + @(".gitignore", $script:CliTargetRelative)
    foreach ($relative in @($targets | Select-Object -Unique)) {
        $target = Join-Path $script:TargetDir $relative
        $snapshot = Join-Path $rollbackRoot $relative
        $existed = Test-Path $target
        if ($existed) {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $snapshot) | Out-Null
            Copy-Item -LiteralPath $target -Destination $snapshot -Force
        }
        $state += [pscustomobject]@{ Relative = $relative; Existed = $existed; Snapshot = $snapshot }
    }
    return $state
}

function Restore-CliBundleState([object[]]$State) {
    foreach ($entry in $State) {
        $target = Join-Path $script:TargetDir $entry.Relative
        if ($entry.Existed) {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
            Copy-Item -LiteralPath $entry.Snapshot -Destination $target -Force
        } elseif (Test-Path $target) {
            Remove-Item -LiteralPath $target -Force
        }
    }
    [Console]::Error.WriteLine("Warning: optional CLI bundle failed; restored its previous files.")
}

function Install-CliBundle {
    if (!$script:InstallCli) { return }

    Initialize-CliIdentity
    $files = @(Get-CliBundleFiles)
    if ($DryRun) {
        foreach ($file in $files) { Copy-HarnessFile $file }
        Merge-Gitignore (Join-Path $script:TargetDir ".gitignore")
        Write-CliBinaryPlan
        return
    }

    $stageRoot = Join-Path $script:TargetDir (".harness-cli-stage." + [guid]::NewGuid().ToString("N"))
    $priorSource = $script:Source
    $state = $null
    New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null
    try {
        foreach ($file in $files) {
            $staged = Join-Path $stageRoot $file
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $staged) | Out-Null
            Write-SourceFile $file $staged
        }
        Stage-HarnessCliBinary $stageRoot
        $state = @(Save-CliBundleState $files $stageRoot)

        $script:Source = @{ Mode = "local"; Root = $stageRoot }
        foreach ($file in $files) { Copy-HarnessFile $file }
        $script:Source = $priorSource
        Merge-Gitignore (Join-Path $script:TargetDir ".gitignore")
        Install-StagedHarnessCliBinary $stageRoot
    } catch {
        $script:Source = $priorSource
        if ($null -ne $state) { Restore-CliBundleState $state }
        throw
    } finally {
        $script:Source = $priorSource
        Remove-Item -LiteralPath $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$script:Created = 0
$script:Updated = 0
$script:Skipped = 0
$script:Source = Get-SourceMode
$script:SourceBaseUrl = if ($env:HARNESS_SOURCE_BASE_URL) { $env:HARNESS_SOURCE_BASE_URL.TrimEnd("/") } else { "https://raw.githubusercontent.com/hoangnb24/repository-harness/main" }
$script:CoreSourceBaseUrl = if ($env:HARNESS_CORE_SOURCE_BASE_URL) { $env:HARNESS_CORE_SOURCE_BASE_URL.TrimEnd("/") } else { "https://raw.githubusercontent.com/hoangnb24/repository-harness/main" }
$script:PayloadManifest = "scripts/harness-install-files.txt"
$script:CliPayloadManifest = "scripts/harness-cli-install-files.txt"
$script:SchemaDir = "scripts/schema"
$script:InstallCli = $WithCli -or $UpgradeCli
$script:CliBaseUrl = ""

if (!$UpgradeCli -and ![string]::IsNullOrWhiteSpace($Ref)) {
    Fail "-Ref is valid only with -UpgradeCli"
}

if ($UpgradeCli) {
    if ([string]::IsNullOrWhiteSpace($Ref)) {
        Fail "-UpgradeCli requires -Ref <harness-cli-vX.Y.Z>"
    }
    if ($Ref -notmatch '^harness-cli-v[0-9]+\.[0-9]+\.[0-9]+(?:[-.][A-Za-z0-9]+)*$') {
        Fail "-Ref must be an immutable Harness CLI release tag such as harness-cli-v0.1.14"
    }
    $script:Source = @{ Mode = "remote"; Root = "" }
    $script:SourceBaseUrl = if ($env:HARNESS_SOURCE_BASE_URL) { $env:HARNESS_SOURCE_BASE_URL.TrimEnd("/") } else { "https://raw.githubusercontent.com/hoangnb24/repository-harness/$Ref" }
    $script:CliBaseUrl = if ($env:HARNESS_CLI_BASE_URL) { $env:HARNESS_CLI_BASE_URL.TrimEnd("/") } else { "https://github.com/hoangnb24/repository-harness/releases/download/$Ref" }
    $RefreshAgentShim = $true
}
if ($script:InstallCli -and [string]::IsNullOrWhiteSpace($script:CliBaseUrl)) {
    $script:CliBaseUrl = if ($env:HARNESS_CLI_BASE_URL) { $env:HARNESS_CLI_BASE_URL.TrimEnd("/") } else { Get-DefaultCliBaseUrl }
}
$script:TargetDir = Resolve-TargetPath $Directory
$script:BackupDir = Join-Path $script:TargetDir (".harness-backup/" + (Get-Date -Format "yyyyMMddHHmmss"))
$script:ConflictAction = "install"

if ($Merge -and $Override) {
    Fail "Use only one of -Merge or -Override"
}

if (!$DryRun -and !(Test-Path $script:TargetDir)) {
    New-Item -ItemType Directory -Force -Path $script:TargetDir | Out-Null
}

$protectedPaths = @("AGENTS.md", "docs")
if ($script:InstallCli) { $protectedPaths += "scripts" }
$conflicts = $protectedPaths | Where-Object { Test-Path (Join-Path $script:TargetDir $_) }
if ($conflicts.Count -gt 0) {
    if ($Merge) {
        $script:ConflictAction = "merge"
        Write-Step "Continuing with merge. Existing files will be skipped."
    } elseif ($Override) {
        $script:ConflictAction = "override"
        foreach ($protected in $protectedPaths) {
            $path = Join-Path $script:TargetDir $protected
            if (!(Test-Path $path)) { continue }
            if ($DryRun) {
                Write-Step "override $protected (backup first)"
            } else {
                New-Item -ItemType Directory -Force -Path $script:BackupDir | Out-Null
                Move-Item -LiteralPath $path -Destination (Join-Path $script:BackupDir $protected)
                Write-Step "removed  $protected (backup: $($script:BackupDir.Substring($script:TargetDir.Length + 1))/$protected)"
            }
        }
    } elseif ($Yes) {
        Fail "target already contains protected Harness paths: $($conflicts -join ', '). Use -Merge or -Override."
    } else {
        Write-Host "Warning: target already contains protected Harness paths: $($conflicts -join ', ')"
        $choice = Read-Host "Choose Merge, Override, or Stop [Stop]"
        switch -Regex ($choice) {
            "^(m|merge)$" { $script:ConflictAction = "merge"; Write-Step "Continuing with merge. Existing files will be skipped." }
            "^(o|override)$" {
                $script:ConflictAction = "override"
                foreach ($protected in $protectedPaths) {
                    $path = Join-Path $script:TargetDir $protected
                    if (Test-Path $path) {
                        New-Item -ItemType Directory -Force -Path $script:BackupDir | Out-Null
                        Move-Item -LiteralPath $path -Destination (Join-Path $script:BackupDir $protected)
                    }
                }
            }
            default { Fail "installation stopped" }
        }
    }
}

if ($script:Source.Mode -eq "local") {
    Write-Step "Harness source: $($script:Source.Root)"
} else {
    Write-Step "Harness source: $script:SourceBaseUrl"
}
if ($script:InstallCli) {
    Write-Step "Harness profile: core+cli"
    Write-Step "Harness CLI source: $script:CliBaseUrl"
} else {
    Write-Step "Harness profile: core"
    Write-Step "Harness CLI source: skipped"
}
Write-Step "Target project: $script:TargetDir"

Install-HarnessCore

Refresh-AgentShimFile
Install-CliBundle

Write-Step ""
Write-Step "Done. Created: $script:Created, updated: $script:Updated, skipped: $script:Skipped."
if ($script:Skipped -gt 0 -and !$Force) {
    Write-Step "Existing files were left untouched. Re-run with -Force to overwrite with backups."
}
if ($Force -and $script:Updated -gt 0 -and !$DryRun) {
    Write-Step "Backups were written to: $script:BackupDir"
}
