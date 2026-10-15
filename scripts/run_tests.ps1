# ==============================================================================
# RestoreLab -- Test Suite Runner for Windows
# ==============================================================================

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Running RestoreLab Test Suite (pytest)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

python -m pytest tests/unit tests/integration -v --durations=10
