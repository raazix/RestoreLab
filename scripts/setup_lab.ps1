# ==============================================================================
# RestoreLab — One-Click Environment Setup Script for Windows
# ==============================================================================

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  RestoreLab: Reliability Environment Setup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Environment file setup
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path $EnvFile)) {
    Write-Host "[INFO] Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item $EnvExample $EnvFile
} else {
    Write-Host "[OK] .env configuration file exists." -ForegroundColor Green
}

# 2. Directory structure setup
$Dirs = @(
    "data",
    "data/lab_repo",
    "data/lab_source",
    "data/lab_restore",
    "data/lab_experiments",
    "bin"
)
foreach ($d in $Dirs) {
    $p = Join-Path $ProjectRoot $d
    if (-not (Test-Path $p)) {
        New-Item -ItemType Directory -Force -Path $p | Out-Null
    }
}
Write-Host "[OK] Lab directory structures verified." -ForegroundColor Green

# 3. Restic executable check
$ResticScript = Join-Path $PSScriptRoot "download_restic.ps1"
& $ResticScript

# 4. Generate sample lab dataset
Write-Host "[INFO] Generating test dataset in data/lab_source..." -ForegroundColor Cyan
python -c "import sys; sys.path.insert(0, 'src'); from restorelab.verification.sample_data import generate_lab_dataset; from restorelab.config import get_settings; s = get_settings(); f, b = generate_lab_dataset(s.resolved_source_dir); print(f'Created {f} files ({b} bytes)')"

# 5. Initialize lab repository if needed
Write-Host "[INFO] Verifying Restic repository..." -ForegroundColor Cyan
python -c "import sys; sys.path.insert(0, 'src'); from restorelab.backup.restic import ResticBackupEngine; from restorelab.config import get_settings; e = ResticBackupEngine(get_settings()); s = e.get_status(); print('Repo status: initialized =', s.initialized); e.init_repository() if not s.initialized else None"

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "[SUCCESS] Setup complete! Launch app via: .\scripts\run_app.ps1" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
