param(
    [Parameter(Mandatory = $true)][string]$Artifact,
    [Parameter(Mandatory = $true)][string]$Checksum,
    [Parameter(Mandatory = $true)][string]$Workspace
)

$ErrorActionPreference = "Stop"
$Installer = Join-Path $PSScriptRoot "../../scripts/install-harness-v1.ps1"
$PowerShellExe = (Get-Process -Id $PID).Path
$Destination = Join-Path $Workspace "must-not-be-created"
$Expected = "Harness V1 installer refused: safe Windows destination publication is controlled-unsupported before mutation"

if (Test-Path -LiteralPath $Workspace) {
    throw "Windows controlled-unsupported test workspace must be new"
}
$ArtifactBefore = (Get-FileHash -LiteralPath $Artifact -Algorithm SHA256).Hash
$ChecksumBefore = (Get-FileHash -LiteralPath $Checksum -Algorithm SHA256).Hash

$Output = & $PowerShellExe -NoProfile -File $Installer `
    -Artifact $Artifact `
    -Checksum $Checksum `
    -Platform windows-x64 `
    -Directory $Destination 2>&1

if ($LASTEXITCODE -ne 1) {
    throw "Harness V1 PowerShell installer did not return controlled unsupported"
}
if (($Output -join "`n") -ne $Expected) {
    throw "Harness V1 PowerShell installer refusal changed: $Output"
}
if (Test-Path -LiteralPath $Workspace) {
    throw "Harness V1 PowerShell installer created destination state before refusal"
}
if ((Get-FileHash -LiteralPath $Artifact -Algorithm SHA256).Hash -ne $ArtifactBefore -or
    (Get-FileHash -LiteralPath $Checksum -Algorithm SHA256).Hash -ne $ChecksumBefore) {
    throw "Harness V1 PowerShell installer changed authenticated inputs"
}

Write-Host "Harness V1 PowerShell installer authenticated native bytes and refused before destination mutation"
