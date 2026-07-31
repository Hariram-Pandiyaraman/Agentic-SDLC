$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Project virtual environment not found. Run: python -m venv .venv"
}

Set-Location -LiteralPath $projectRoot
& $pythonExe -m uvicorn api.main:app --reload --port 8000

