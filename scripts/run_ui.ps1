$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$streamlitExe = Join-Path $projectRoot ".venv\Scripts\streamlit.exe"

if (-not (Test-Path -LiteralPath $streamlitExe)) {
    throw "Streamlit is not installed in the project virtual environment."
}

Set-Location -LiteralPath $projectRoot
& $streamlitExe run app\streamlit_app.py

