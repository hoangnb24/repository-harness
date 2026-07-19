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

function Assert-NoReparseComponents([string]$Path, [string]$Label) {
    $FullPath = [IO.Path]::GetFullPath($Path)
    $PathRoot = [IO.Path]::GetPathRoot($FullPath)
    $Cursor = $PathRoot
    $Remainder = $FullPath.Substring($PathRoot.Length)
    $Separators = [char[]]@([IO.Path]::DirectorySeparatorChar)
    foreach ($Component in $Remainder.Split($Separators, [StringSplitOptions]::RemoveEmptyEntries)) {
        $Cursor = Join-Path $Cursor $Component
        if (Test-Path -LiteralPath $Cursor) {
            $Item = Get-Item -LiteralPath $Cursor -Force
            if ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                Refuse "$Label contains a link or reparse point: $Cursor"
            }
        }
    }
    return $FullPath
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

if (![IO.Path]::IsPathRooted($Directory)) { Refuse "target directory must be an absolute path" }
$RootPath = Assert-NoReparseComponents $Directory "target directory"
if (!(Test-Path -LiteralPath $RootPath -PathType Container)) { Refuse "target directory is missing or is not a directory" }
$RootItem = Get-Item -LiteralPath $RootPath -Force
if ($RootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) { Refuse "target directory is a link or reparse point" }
$RootPath = $RootItem.FullName.TrimEnd([IO.Path]::DirectorySeparatorChar)
if ($RootPath -eq [IO.Path]::GetPathRoot($RootPath)) { Refuse "target directory cannot be the filesystem root" }

$ScriptsDirectory = Join-Path $RootPath "scripts"
if (Test-Path -LiteralPath $ScriptsDirectory) {
    if (!(Test-Path -LiteralPath $ScriptsDirectory -PathType Container)) { Refuse "destination component scripts is not a directory" }
} else {
    [IO.Directory]::CreateDirectory($ScriptsDirectory) | Out-Null
}
$ScriptsDirectory = Assert-NoReparseComponents $ScriptsDirectory "destination component scripts"

$BinDirectory = Join-Path $ScriptsDirectory "bin"
if (Test-Path -LiteralPath $BinDirectory) {
    if (!(Test-Path -LiteralPath $BinDirectory -PathType Container)) { Refuse "destination component scripts/bin is not a directory" }
} else {
    [IO.Directory]::CreateDirectory($BinDirectory) | Out-Null
}
$BinDirectory = Assert-NoReparseComponents $BinDirectory "destination component scripts/bin"
$RootPrefix = $RootPath + [IO.Path]::DirectorySeparatorChar
if (!$BinDirectory.StartsWith($RootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    Refuse "destination directory escaped the target root"
}

$Destination = Join-Path $BinDirectory "harness.exe"
if (Test-Path -LiteralPath $Destination) { Refuse "destination already exists" }
$Temporary = Join-Path $BinDirectory (".harness-v1-install." + [guid]::NewGuid().ToString("N"))
try {
    $VerifiedBinDirectory = Assert-NoReparseComponents $BinDirectory "destination component scripts/bin"
    if (!$VerifiedBinDirectory.Equals($BinDirectory, [StringComparison]::OrdinalIgnoreCase)) {
        Refuse "destination directory identity changed before copy"
    }
    Copy-Item -LiteralPath $Artifact -Destination $Temporary
    $Installed = (Get-FileHash -LiteralPath $Temporary -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Installed -ne $Expected) { Refuse "installed copy changed after authentication" }
    $VerifiedBinDirectory = Assert-NoReparseComponents $BinDirectory "destination component scripts/bin"
    if (!$VerifiedBinDirectory.Equals($BinDirectory, [StringComparison]::OrdinalIgnoreCase)) {
        Refuse "destination directory identity changed before publication"
    }
    if (Test-Path -LiteralPath $Destination) { Refuse "destination appeared during install" }
    [IO.File]::Move($Temporary, $Destination)
} finally {
    if (Test-Path -LiteralPath $Temporary) {
        Move-Item -LiteralPath $Temporary -Destination "$Temporary.failed" -Force
    }
}
Write-Output "Installed checksum-verified Harness V1 artifact at scripts/bin/harness.exe; provenance and platform acceptance remain unclaimed."
