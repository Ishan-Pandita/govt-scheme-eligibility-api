param(
    [switch]$SkipSeed
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $Python = "python"
}

$env:REDIS_URL = "memory://local"

& $Python -m alembic upgrade head

if (-not $SkipSeed) {
    & $Python seed.py
}

& $Python -m uvicorn app.main:app --reload
