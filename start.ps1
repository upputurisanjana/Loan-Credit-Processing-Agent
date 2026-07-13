# start.ps1 - Start the Credit Decisioning Agent (backend + frontend) on Windows
#
# Usage:
#   .\start.ps1              # start backend + frontend (default)
#   .\start.ps1 backend      # backend only
#   .\start.ps1 frontend     # frontend only
#   .\start.ps1 demo         # start both + auto-submit the clear_approve fixture
#
# If you see execution policy errors, run once as Admin:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Mode = "both",

    [Parameter(Position = 1)]
    [string]$Fixture = ""
)

$ErrorActionPreference = "Stop"
$Root         = Split-Path -Parent $MyInvocation.MyCommand.Definition
$BackendPort  = if ($env:BACKEND_PORT)  { $env:BACKEND_PORT  } else { "8000" }
$FrontendPort = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "5173" }
$Venv         = Join-Path $Root ".venv"
$Frontend     = Join-Path $Root "frontend"
$Uvicorn      = Join-Path $Venv "Scripts\uvicorn.exe"

function Info { param($msg) Write-Host "[info]  $msg" -ForegroundColor Cyan }
function Ok   { param($msg) Write-Host "[ok]    $msg" -ForegroundColor Green }
function Warn { param($msg) Write-Host "[warn]  $msg" -ForegroundColor Yellow }
function Err  { param($msg) Write-Host "[error] $msg" -ForegroundColor Red; exit 1 }

# Pre-flight checks
function Test-Environment {
    Info "Checking environment..."

    $envFile = Join-Path $Root ".env"
    if (-not (Test-Path $envFile)) {
        Err ".env not found. Run .\setup.ps1 first, then add your GITHUB_TOKEN."
    }

    $token = (Get-Content $envFile | Where-Object { $_ -match "^GITHUB_TOKEN=" }) -replace "^GITHUB_TOKEN=", ""
    if ($token) { $token = $token.Trim() }
    if (-not $token) {
        Err "GITHUB_TOKEN is empty in .env - add your GitHub PAT (models:read scope)."
    }

    if (-not (Test-Path $Venv)) {
        Err ".venv not found. Run .\setup.ps1 first."
    }
    $cfgFile = Join-Path $Venv "pyvenv.cfg"
    if (Test-Path $cfgFile) {
        $cfgContent = Get-Content $cfgFile -Raw
        if ($cfgContent -match "home\s*=\s*/") {
            Err "Your .venv is a WSL/Linux venv and won't work on Windows. Run .\setup.ps1 to recreate it."
        }
    }
    if (-not (Test-Path $Uvicorn)) {
        Err "uvicorn not found in .venv. Run .\setup.ps1 to install dependencies."
    }

    try { & node --version | Out-Null } catch { Err "node not found - install Node.js 18+ from https://nodejs.org" }
    try { & npm  --version | Out-Null } catch { Err "npm not found" }

    $nodeModules = Join-Path $Frontend "node_modules"
    if (-not (Test-Path $nodeModules)) {
        Warn "node_modules missing - running npm install..."
        Push-Location $Frontend
        & npm install --silent
        Pop-Location
    }

    Ok "Environment OK"
}

# Backend: run uvicorn as a background job
$BackendJob = $null
function Start-Backend {
    Info "Starting FastAPI backend on http://localhost:${BackendPort} ..."
    $script:BackendJob = Start-Job -ScriptBlock {
        param($uvicorn, $port, $root)
        Set-Location $root
        & $uvicorn app.main:app --reload --port $port --log-level info --host 0.0.0.0
    } -ArgumentList $Uvicorn, $BackendPort, $Root
    Ok "Backend starting (job $($BackendJob.Id)) - docs at http://localhost:${BackendPort}/docs"
}

# Frontend: run npm run dev as a background job
$FrontendJob = $null
function Start-Frontend {
    Info "Starting Vite frontend on http://localhost:${FrontendPort} ..."
    $script:FrontendJob = Start-Job -ScriptBlock {
        param($frontend, $port, $apiUrl)
        Set-Location $frontend
        $env:VITE_API_URL = $apiUrl
        & npm run dev -- --port $port
    } -ArgumentList $Frontend, $FrontendPort, "http://localhost:${BackendPort}"
    Ok "Frontend starting (job $($FrontendJob.Id)) - open http://localhost:${FrontendPort}"
}

# Wait for backend /health
function Wait-Backend {
    Info "Waiting for backend to be ready..."
    $attempts = 0
    while ($true) {
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:${BackendPort}/health" `
                -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) { break }
        } catch {}
        Start-Sleep -Seconds 1
        $attempts++
        if ($attempts -gt 30) {
            Warn "Backend didn't respond in 30s - skipping health check."
            return
        }
    }
    Ok "Backend is ready."
}

# Demo: submit the clear_approve fixture
function Submit-Demo {
    $fix = if ($Fixture) { $Fixture } else { Join-Path $Root "tests\fixtures\clear_approve.json" }
    if (-not (Test-Path $fix)) { Warn "Fixture not found: $fix"; return }
    Wait-Backend
    Info "Submitting demo application from $fix ..."
    $body = Get-Content $fix -Raw
    try {
        $resp = Invoke-RestMethod -Method Post `
            -Uri "http://localhost:${BackendPort}/applications" `
            -ContentType "application/json" -Body $body
        $resp | ConvertTo-Json -Depth 10
    } catch {
        Warn "Demo submit failed: $_"
    }
    Ok "Demo app submitted - open http://localhost:${FrontendPort} to see the queue."
}

# Stream job output to console
function Receive-Jobs {
    if ($BackendJob)  { Receive-Job -Job $BackendJob  -ErrorAction SilentlyContinue | Write-Host }
    if ($FrontendJob) { Receive-Job -Job $FrontendJob -ErrorAction SilentlyContinue | Write-Host }
}

# Cleanup on Ctrl-C / exit
function Stop-All {
    Info "Shutting down..."
    if ($BackendJob)  { Stop-Job -Job $BackendJob;  Remove-Job -Job $BackendJob  -Force }
    if ($FrontendJob) { Stop-Job -Job $FrontendJob; Remove-Job -Job $FrontendJob -Force }
    Ok "Stopped."
}

# Main
Test-Environment

switch ($Mode) {
    "backend" {
        Start-Backend
        Info "Backend running. Press Ctrl-C to stop."
        try { while ($true) { Receive-Jobs; Start-Sleep -Seconds 2 } }
        finally { Stop-All }
    }
    "frontend" {
        Start-Frontend
        Info "Frontend running. Press Ctrl-C to stop."
        try { while ($true) { Receive-Jobs; Start-Sleep -Seconds 2 } }
        finally { Stop-All }
    }
    "demo" {
        Start-Backend
        Start-Frontend
        Submit-Demo
        Info "Both servers running. Press Ctrl-C to stop."
        try { while ($true) { Receive-Jobs; Start-Sleep -Seconds 2 } }
        finally { Stop-All }
    }
    default {
        Start-Backend
        Start-Frontend
        Write-Host ""
        Write-Host "----------------------------------------------------" -ForegroundColor White
        Write-Host "  Backend  ->  http://localhost:${BackendPort}/docs" -ForegroundColor Green
        Write-Host "  Frontend ->  http://localhost:${FrontendPort}"     -ForegroundColor Green
        Write-Host "----------------------------------------------------" -ForegroundColor White
        Write-Host "  Press Ctrl-C to stop both servers." -ForegroundColor White
        Write-Host ""
        try { while ($true) { Receive-Jobs; Start-Sleep -Seconds 2 } }
        finally { Stop-All }
    }
}
