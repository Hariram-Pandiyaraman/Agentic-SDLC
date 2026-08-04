$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $projectRoot "frontend"
$packageFile = Join-Path $frontendRoot "package.json"
$modules = Join-Path $frontendRoot "node_modules"

if (-not (Test-Path -LiteralPath $packageFile)) {
    throw "The React frontend package was not found at $frontendRoot."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js and npm are required to run the React frontend."
}

if (-not (Test-Path -LiteralPath $modules)) {
    throw "Frontend dependencies are missing. Run: npm install --prefix frontend"
}

Set-Location -LiteralPath $frontendRoot
& npm.cmd run dev
