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

$Invocation = '$ProgressPreference = "SilentlyContinue"; & $env:HARNESS_V1_TEST_INSTALLER -Artifact $env:HARNESS_V1_TEST_ARTIFACT -Checksum $env:HARNESS_V1_TEST_CHECKSUM -Platform windows-x64 -Directory $env:HARNESS_V1_TEST_DESTINATION'
$EncodedInvocation = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Invocation))
$StartInfo = New-Object System.Diagnostics.ProcessStartInfo
$StartInfo.FileName = $PowerShellExe
$StartInfo.Arguments = "-NoLogo -NoProfile -NonInteractive -OutputFormat Text -EncodedCommand $EncodedInvocation"
$StartInfo.UseShellExecute = $false
$StartInfo.CreateNoWindow = $true
$StartInfo.RedirectStandardOutput = $true
$StartInfo.RedirectStandardError = $true
$StartInfo.EnvironmentVariables["HARNESS_V1_TEST_INSTALLER"] = $Installer
$StartInfo.EnvironmentVariables["HARNESS_V1_TEST_ARTIFACT"] = $Artifact
$StartInfo.EnvironmentVariables["HARNESS_V1_TEST_CHECKSUM"] = $Checksum
$StartInfo.EnvironmentVariables["HARNESS_V1_TEST_DESTINATION"] = $Destination

$Process = New-Object System.Diagnostics.Process
$Process.StartInfo = $StartInfo
try {
    if (!$Process.Start()) {
        throw "Harness V1 PowerShell installer process did not start"
    }
    $StandardOutputTask = $Process.StandardOutput.ReadToEndAsync()
    $StandardErrorTask = $Process.StandardError.ReadToEndAsync()
    $Process.WaitForExit()
    $ExitCode = $Process.ExitCode
    $StandardOutput = $StandardOutputTask.GetAwaiter().GetResult()
    $StandardError = $StandardErrorTask.GetAwaiter().GetResult()
} finally {
    $Process.Dispose()
}

if ($ExitCode -ne 1) {
    throw "Harness V1 PowerShell installer did not return controlled unsupported"
}
if ($StandardOutput -ne "") {
    throw "Harness V1 PowerShell installer wrote unexpected stdout: $StandardOutput"
}
$ExpectedStandardError = $Expected + [Environment]::NewLine
if ($StandardError -ne $ExpectedStandardError) {
    throw "Harness V1 PowerShell installer refusal changed: $StandardError"
}
if (Test-Path -LiteralPath $Workspace) {
    throw "Harness V1 PowerShell installer created destination state before refusal"
}
if ((Get-FileHash -LiteralPath $Artifact -Algorithm SHA256).Hash -ne $ArtifactBefore -or
    (Get-FileHash -LiteralPath $Checksum -Algorithm SHA256).Hash -ne $ChecksumBefore) {
    throw "Harness V1 PowerShell installer changed authenticated inputs"
}

Write-Host "Harness V1 PowerShell installer authenticated native bytes and refused before destination mutation"
