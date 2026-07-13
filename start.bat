@echo off
REM start.bat — CMD wrapper for start.ps1
REM
REM Usage:
REM   start.bat            (start backend + frontend)
REM   start.bat backend
REM   start.bat frontend
REM   start.bat demo
REM
REM This just calls start.ps1 with the same arguments via PowerShell.

setlocal
set "ROOT=%~dp0"
set "MODE=%~1"

if "%MODE%"=="" set "MODE=both"

powershell.exe -NoLogo -ExecutionPolicy Bypass -File "%ROOT%start.ps1" %MODE% %2
