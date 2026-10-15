# ==============================================================================
# RestoreLab -- Restic Binary Downloader for Windows
# ==============================================================================

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BinDir = Join-Path $ProjectRoot "bin"
$ResticExe = Join-Path $BinDir "restic.exe"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  RestoreLab: Restic Executable Setup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (Test-Path $ResticExe) {
    Write-Host "[OK] Restic binary already exists at: $ResticExe" -ForegroundColor Green
    & $ResticExe version
    exit 0
}

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

Write-Host "[INFO] Fetching latest release asset from GitHub API..." -ForegroundColor Yellow
$ApiUrl = "https://api.github.com/repos/restic/restic/releases/latest"
$Release = Invoke-RestMethod -Uri $ApiUrl -Headers @{ "User-Agent" = "RestoreLab" }
$Asset = $Release.assets | Where-Object { $_.name -like "*windows_amd64.zip" } | Select-Object -First 1

if (-not $Asset) {
    Write-Host "[WARN] Could not find windows_amd64.zip release asset. Using known stable fallback URL..." -ForegroundColor Yellow
    $DownloadUrl = "https://github.com/restic/restic/releases/download/v0.19.1/restic_0.19.1_windows_amd64.zip"
    $ZipName = "restic_0.19.1_windows_amd64.zip"
} else {
    $DownloadUrl = $Asset.browser_download_url
    $ZipName = $Asset.name
}

$ZipPath = Join-Path $BinDir $ZipName
Write-Host "[INFO] Downloading from $DownloadUrl..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipPath -UseBasicParsing

Write-Host "[INFO] Extracting archive..." -ForegroundColor Cyan
Expand-Archive -Path $ZipPath -DestinationPath $BinDir -Force

$Extracted = Get-ChildItem -Path $BinDir -Filter "restic*.exe" | Where-Object { $_.Name -ne "restic.exe" } | Select-Object -First 1
if ($Extracted) {
    Copy-Item -Path $Extracted.FullName -Destination $ResticExe -Force
}

Remove-Item -Path $ZipPath -Force -ErrorAction SilentlyContinue

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "[SUCCESS] Restic configured successfully:" -ForegroundColor Green
& $ResticExe version
Write-Host "==========================================================" -ForegroundColor Green
