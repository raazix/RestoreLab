# ==============================================================================
# RestoreLab -- Application Launch Script for Windows
# Launches FastAPI backend serving the pre-built React workbench on http://localhost:8000
# ==============================================================================

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  Launching RestoreLab -- Reliability Engineering Workbench" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location -Path $ProjectRoot

# Check if frontend is built
if (-not (Test-Path "$ProjectRoot\frontend\dist\index.html")) {
    Write-Host "[*] Building React frontend..." -ForegroundColor Yellow
    Set-Location -Path "$ProjectRoot\frontend"
    npm run build
    Set-Location -Path $ProjectRoot
}

Write-Host "[*] Starting Uvicorn API server on http://localhost:8000" -ForegroundColor Green
Write-Host "[*] Open http://localhost:8000 in your browser." -ForegroundColor Green
Write-Host "[*] Press Ctrl+C to terminate." -ForegroundColor DarkGray

Start-Process "http://localhost:8000"

python -m uvicorn src.restorelab.api.main:app --host 127.0.0.1 --port 8000
