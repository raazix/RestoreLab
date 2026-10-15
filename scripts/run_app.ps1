# ==============================================================================
# RestoreLab — Application Launch Script for Windows
# ==============================================================================

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Launching RestoreLab Streamlit Workbench..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

python -m streamlit run app.py --server.port 8501 --server.headless false
