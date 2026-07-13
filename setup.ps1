# setup.ps1 - One-time environment setup for Windows
# Run this first, then use start.ps1 to launch the app.
#
# Usage (PowerShell):
#   .\setup.ps1
#
# If you see execution policy errors, run once as Admin:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition

function Info    { param($msg) Write-Host "[info]  $msg" -ForegroundColor Cyan }
function Ok      { param($msg) Write-Host "[ok]    $msg" -ForegroundColor Green }
function Warn    { param($msg) Write-Host "[warn]  $msg" -ForegroundColor Yellow }
function Err     { param($msg) Write-Host "[error] $msg" -ForegroundColor Red; exit 1 }

# 1. Delete stale WSL/Linux venv if present
$venv = Join-Path $Root ".venv"
if (Test-Path $venv) {
    $cfg = Join-Path $venv "pyvenv.cfg"
    $isLinuxVenv = $false
    if (Test-Path $cfg) {
        $cfgContent = Get-Content $cfg -Raw
        if ($cfgContent -match "home\s*=\s*/") {
            $isLinuxVenv = $true
        }
    }
    if ($isLinuxVenv) {
        Warn "Found a WSL/Linux venv (home = /usr/bin) - removing it."
        Remove-Item -Recurse -Force $venv
        Ok "Removed old Linux venv."
    } else {
        Info ".venv already exists and looks like a Windows venv - skipping recreation."
        Info "Delete .venv manually and re-run this script if you hit import errors."
    }
}

# 2. Check Python
Info "Checking Python..."
$py = $null
foreach ($candidate in @("python", "python3", "py")) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python 3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 10) {
                $py = $candidate
                Ok "Using: $ver"
                break
            }
        }
    } catch {}
}
if (-not $py) {
    Err "Python 3.10+ not found. Install from https://www.python.org/downloads/ (tick 'Add to PATH')."
}

# 3. Create Windows venv
if (-not (Test-Path $venv)) {
    Info "Creating .venv..."
    & $py -m venv $venv
    Ok ".venv created."
}

# 4. Install Python dependencies
$pip = Join-Path $venv "Scripts\pip.exe"
$reqFile = Join-Path $Root "requirements.txt"
Info "Installing Python dependencies from requirements.txt..."
& $pip install --upgrade pip --quiet
& $pip install -r $reqFile
Ok "Python dependencies installed."

# 5. Check Node.js
Info "Checking Node.js..."
try {
    $nodeVer = & node --version 2>&1
    Ok "Node: $nodeVer"
} catch {
    Err "Node.js not found. Install from https://nodejs.org (LTS recommended)."
}

# 6. Install frontend node_modules
$frontend = Join-Path $Root "frontend"
if (Test-Path (Join-Path $frontend "package.json")) {
    Info "Installing frontend dependencies (npm install)..."
    Push-Location $frontend
    & npm install --silent
    Pop-Location
    Ok "Frontend dependencies installed."
} else {
    Warn "frontend/package.json not found - skipping npm install."
}

# 7. Create .env if missing
$envFile    = Join-Path $Root ".env"
$envExample = Join-Path $Root ".env.example"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Ok "Created .env from .env.example"
        Warn "Open .env and set GITHUB_TOKEN before running start.ps1"
    } else {
        Warn ".env.example not found - create .env manually."
    }
} else {
    Info ".env already exists."
}

Write-Host ""
Write-Host "----------------------------------------------------" -ForegroundColor White
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "  1. Edit .env and set your GITHUB_TOKEN" -ForegroundColor White
Write-Host "  2. Run .\start.ps1 to launch backend + frontend" -ForegroundColor White
Write-Host "----------------------------------------------------" -ForegroundColor White
