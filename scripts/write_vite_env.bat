@echo off
REM Write the real .env.local for Vite, using the JARVIS_DASHBOARD_DEV_TOKEN
REM env var that you just set in your shell.
REM
REM Run this in cmd.exe (not bash) after setting the env var:
REM   set JARVIS_DASHBOARD_DEV_TOKEN=GoN_Z7W_4M6wM2x-lsU-kDN4RWXrC1ZL_XIk7hjTwuA
REM   scripts\write_vite_env.bat
REM
REM Or in PowerShell:
REM   $env:JARVIS_DASHBOARD_DEV_TOKEN = "GoN_Z7W_4M6wM2x-lsU-kDN4RWXrC1ZL_XIk7hjTwuA"
REM   .\scripts\write_vite_env.bat

if "%JARVIS_DASHBOARD_DEV_TOKEN%"=="" (
    echo ERROR: JARVIS_DASHBOARD_DEV_TOKEN env var is not set.
    echo Run your shell first to set it, then re-run this script.
    exit /b 1
)

> frontend-react\.env.local echo # Vite env - auto-loaded by Vite on start. Local dev only.
>> frontend-react\.env.local echo VITE_API_BASE=/api/plugins/jarvis-dashboard/v1
>> frontend-react\.env.local echo VITE_TOKEN=%JARVIS_DASHBOARD_DEV_TOKEN%
>> frontend-react\.env.local echo VITE_WS_URL=ws://localhost:5173/api/plugins/jarvis-dashboard/v1/ws

echo.
echo Wrote frontend-react\.env.local with real token.
echo.
type frontend-react\.env.local
