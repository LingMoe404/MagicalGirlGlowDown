param(
    [string]$WheelPath,
    [string]$HelperPath
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $WheelPath) {
    $distDir = Join-Path $repoRoot "dist"
    $wheel = Get-ChildItem -LiteralPath $distDir -Filter "*.whl" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $wheel) {
        throw "No wheel was found in $distDir"
    }
    $WheelPath = $wheel.FullName
}
if (-not $HelperPath) {
    $HelperPath = Join-Path $repoRoot "src\magical_girl_glow_down\gigabyte_helper\MagicalGirlGlowDown.GigabyteHelper.exe"
}

if (-not (Test-Path -LiteralPath $WheelPath)) {
    throw "Wheel not found: $WheelPath"
}
if (-not (Test-Path -LiteralPath $HelperPath)) {
    throw "Helper executable not found: $HelperPath"
}

$helperEntryNames = @(
    "magical_girl_glow_down/gigabyte_helper/MagicalGirlGlowDown.GigabyteHelper.exe",
    "src/magical_girl_glow_down/gigabyte_helper/MagicalGirlGlowDown.GigabyteHelper.exe"
)
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Get-Sha256Hex {
    param(
        [System.IO.Stream]$Stream
    )

    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha256.ComputeHash($Stream)
        return ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
    }
    finally {
        $sha256.Dispose()
    }
}

$wheelZip = [System.IO.Compression.ZipFile]::OpenRead($WheelPath)
try {
    $entry = $null
    foreach ($candidate in $helperEntryNames) {
        $entry = $wheelZip.GetEntry($candidate)
        if ($entry) {
            break
        }
    }
    if (-not $entry) {
        throw "Wheel does not contain the helper executable"
    }
    $entryStream = $entry.Open()
    try {
        $wheelHash = Get-Sha256Hex -Stream $entryStream
    }
    finally {
        $entryStream.Dispose()
    }
}
finally {
    $wheelZip.Dispose()
}

$helperFile = [System.IO.File]::OpenRead($HelperPath)
try {
    $helperHash = Get-Sha256Hex -Stream $helperFile
}
finally {
    $helperFile.Dispose()
}

if ($wheelHash -ne $helperHash) {
    throw "Wheel helper hash mismatch. Wheel=$wheelHash Helper=$helperHash"
}

Write-Host "Wheel helper hash matches built EXE."
