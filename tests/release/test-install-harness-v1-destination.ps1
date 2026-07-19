param(
    [Parameter(Mandatory = $true)][string]$Artifact,
    [Parameter(Mandatory = $true)][string]$Checksum,
    [Parameter(Mandatory = $true)][string]$Workspace
)

$ErrorActionPreference = "Stop"
$Installer = Join-Path $PSScriptRoot "../../scripts/install-harness-v1.ps1"
$PowerShellExe = (Get-Process -Id $PID).Path
[IO.Directory]::CreateDirectory($Workspace) | Out-Null

foreach ($Attack in @("root-link", "scripts-link", "bin-link")) {
    $Repository = Join-Path $Workspace "repository-$Attack"
    $Outside = Join-Path $Workspace "outside-$Attack"
    [IO.Directory]::CreateDirectory($Outside) | Out-Null
    if ($Attack -eq "root-link") {
        New-Item -ItemType Junction -Path $Repository -Target $Outside | Out-Null
    } else {
        [IO.Directory]::CreateDirectory($Repository) | Out-Null
        if ($Attack -eq "scripts-link") {
            New-Item -ItemType Junction -Path (Join-Path $Repository "scripts") -Target $Outside | Out-Null
        } else {
            $Scripts = Join-Path $Repository "scripts"
            [IO.Directory]::CreateDirectory($Scripts) | Out-Null
            New-Item -ItemType Junction -Path (Join-Path $Scripts "bin") -Target $Outside | Out-Null
        }
    }

    & $PowerShellExe -NoProfile -File $Installer `
        -Artifact $Artifact `
        -Checksum $Checksum `
        -Platform windows-x64 `
        -Directory $Repository *> $null
    if ($LASTEXITCODE -eq 0) {
        throw "Harness V1 PowerShell installer accepted $Attack"
    }
    if (Test-Path -LiteralPath (Join-Path $Outside "harness.exe")) {
        throw "Harness V1 PowerShell installer escaped through $Attack"
    }
}

Write-Host "Harness V1 PowerShell installer rejected root/scripts/bin junction escapes"
