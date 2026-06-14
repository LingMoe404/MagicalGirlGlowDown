$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$project = Join-Path $repoRoot "helper\NollieRGBIdle.GigabyteHelper"
$output = Join-Path $repoRoot "src\nollie_rgb_idle\gigabyte_helper"

if (Test-Path -LiteralPath $output) {
    $resolvedOutput = (Resolve-Path -LiteralPath $output).Path
    $resolvedRepo = (Resolve-Path -LiteralPath $repoRoot).Path
    if (-not $resolvedOutput.StartsWith($resolvedRepo, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean helper output outside the repository."
    }
    Remove-Item -LiteralPath $output -Recurse -Force
}

dotnet publish $project `
    -c Release `
    -r win-x64 `
    --self-contained false `
    -p:PublishSingleFile=true `
    -p:DebugType=None `
    -o $output
