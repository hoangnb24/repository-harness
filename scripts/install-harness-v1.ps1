param(
    [Parameter(Mandatory = $true)][string]$Artifact,
    [Parameter(Mandatory = $true)][string]$Checksum,
    [Parameter(Mandatory = $true)][string]$Platform,
    [Parameter(Mandatory = $true)][string]$Directory
)

$ErrorActionPreference = "Stop"
function Refuse([string]$Message) {
    [Console]::Error.WriteLine("Harness V1 installer refused: $Message")
    exit 1
}

if (!(Test-Path -LiteralPath $Artifact -PathType Leaf)) { Refuse "artifact is missing" }
if (!(Test-Path -LiteralPath $Checksum -PathType Leaf)) { Refuse "checksum is missing" }
$ArtifactItem = Get-Item -LiteralPath $Artifact -Force
$ChecksumItem = Get-Item -LiteralPath $Checksum -Force
if (($ArtifactItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
    ($ChecksumItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    Refuse "artifact and checksum must not be links or reparse points"
}

# Authenticate exact bytes before selecting a platform path or invoking code.
$ChecksumText = [IO.File]::ReadAllText($Checksum)
$Match = [regex]::Match($ChecksumText, '^([0-9a-f]{64})  ([^\\/\r\n]+)\r?\n$')
if (!$Match.Success) { Refuse "checksum must be an exact lowercase SHA-256 and filename record" }
$Expected = $Match.Groups[1].Value
if ($Match.Groups[2].Value -ne $ArtifactItem.Name) { Refuse "checksum does not bind the exact artifact filename" }
$Actual = (Get-FileHash -LiteralPath $Artifact -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Actual -ne $Expected) { Refuse "artifact checksum mismatch" }

if (![System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows) -or
    [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture -ne [System.Runtime.InteropServices.Architecture]::X64) {
    Refuse "unsupported native platform"
}
if ($Platform -ne "windows-x64") { Refuse "platform identity mismatch: expected windows-x64" }
if ($ArtifactItem.Name -ne "harness-windows-x64.exe") { Refuse "artifact filename does not match platform identity" }

# Safe handle-relative/no-follow destination publication is not implemented on
# Windows. Refuse after authenticating bytes and validating the native platform,
# before inspecting or mutating the caller-controlled destination namespace.
Refuse "safe Windows destination publication is controlled-unsupported before mutation"
