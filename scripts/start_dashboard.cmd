@echo off
setlocal EnableDelayedExpansion

REM Reads the 2 secrets from C:\Users\saiyu\jarvis_dashboard_secrets.txt (which YOU created),
REM exports them, writes .env.local, starts the 2 services, and verifies.
REM
REM Step 1: Create the file C:\Users\saiyu\jarvis_dashboard_secrets.txt with 2 lines
REM         (replace the placeholder values with your real ones from set_dashboard_secrets.sh):
REM
REM     JARVIS_DASHBOARD_DEV_TOKEN=put-your-dev-token-here
REM     JARVIS_CONTROL_TOKEN_SECRET=put-your-ctrl-secret-here
REM
REM Step 2: Run this script:
REM     scripts\start_dashboard.cmd

if not exist "%USERPROFILE%\jarvis_dashboard_secrets.txt" (
    echo ERROR: %USERPROFILE%\jarvis_dashboard_secrets.txt not found.
    echo.
    echo Create the file with these 2 lines (replace values with your real ones):
    echo.
    echo     JARVIS_DASHBOARD_DEV_TOKEN=put-your-dev-token-here
    echo     JARVIS_CONTROL_TOKEN_SECRET=put-your-ctrl-secret-here
    echo.
    echo Then re-run this script.
    exit /b 1
)

echo === Loading secrets from %USERPROFILE%\jarvis_dashboard_secrets.txt ===
for /f "usebackq tokens=1,* delims==" %%a in ("%USERPROFILE%\jarvis_dashboard_secrets.txt") do set "%%a=%%b"

if "%JARVIS_DASHBOARD_DEV_TOKEN%"=="" (
    echo ERROR: JARVIS_DASHBOARD_DEV_TOKEN is empty in the secrets file
    exit /b 1
)
if "%JARVIS_CONTROL_TOKEN_SECRET%"=="" (
    echo ERROR: JARVIS_CONTROL_TOKEN_SECRET is empty in the secrets file
    exit /b 1
)

set "LEN_DEV=0"
for /L %%i in (0,1,200) do if not "!JARVIS_DASHBOARD_DEV_TOKEN:~%%i,1!"=="" set "LEN_DEV=%%i"
set /a LEN_DEV+=1

set "LEN_CTRL=0"
for /L %%i in (0,1,200) do if not "!JARVIS_CONTROL_TOKEN_SECRET:~%%i,1!"=="" set "LEN_CTRL=%%i"
set /a LEN_CTRL+=1

echo Loaded:
echo   JARVIS_DASHBOARD_DEV_TOKEN (length=!LEN_DEV!)
echo   JARVIS_CONTROL_TOKEN_SECRET (length=!LEN_CTRL!)

if not !LEN_DEV! GEQ 30 (
    echo ERROR: DEV_TOKEN looks too short. Expected 30+. Check the file.
    exit /b 1
)
if not !LEN_CTRL! GEQ 60 (
    echo ERROR: CTRL_SECRET looks too short. Expected 60+. Check the file.
    exit /b 1
)

cd /d "C:\Users\saiyu\Desktop\projects\KI_projects\hermes_jarvis_war_room"

echo.
echo === Writing frontend-react\.env.local ===
>  frontend-react\.env.local echo # Vite env - auto-loaded by Vite on start. Local dev only.
>> frontend-react\.env.local echo VITE_API_BASE=/api/plugins/jarvis-dashboard/v1
>> frontend-react\.env.local echo VITE_TOKEN=... rem Wait for the file to flush
>nul timeout /t 1 /nobreak

echo Wrote. Preview (token masked):
for /f "tokens=1,* delims==" %%a in (frontend-react\.env.local) do (
    set "LINE=%%a"
    if "!LINE!"=="VITE_TOKEN" (
        echo   VITE_TOKEN=****...!VITE_TOKEN:~-4!  (length=%%b length: !LEN_DEV!)
    ) else (
        echo   %%a=%%b
    )
)

echo.
echo === Killing any old processes on 8502 / 5173 ===
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8502.*LISTENING"') do (
    echo Killing PID %%p on port 8502
    taskkill /F /PID %%p >nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173.*LISTENING"') do (
    echo Killing PID %%p on port 5173
    taskkill /F /PID %%p >nul 2>&1)
timeout /t 3 /nobreak >nul

echo.
echo === Starting FastAPI backend on port 8502 (background) ===
set "JARVIS_CONTROL_TOKEN_SECRET=**%...N_CONTROL_TOKEN...L%."
start /b "uvicorn-jarvis" cmd /c "set JARVIS_CONTROL_TOKEN_SEC...^&^& python -m uvicorn backend.server:app --host 127.0.0.1 --port 8502 > C:\Users\saiyu\AppData\Local\Temp\uvicorn.log 2>&1"
echo Backend launched. Log: C:\Users\saiyu\AppData\Local\Temp\uvicorn.log

echo.
echo === Starting Vite dev server on port 5173 (background) ===
cd frontend-react
start /b "vite-jarvis" cmd /c "npm run dev > C:\Users\saiyu\AppData\Local\Temp\vite.log 2>&1"
echo Vite launched. Log: C:\Users\saiyu\AppData\Local\Temp\vite.log
cd ..

echo.
echo === Waiting 10 seconds for both to bind ===
timeout /t 10 /nobreak >nul

echo.
echo === Verification ===
curl -s -o nul -w "Backend  (8502) health: HTTP %%{http_code}\n" http://127.0.0.1:8502/api/plugins/jarvis-dashboard/health
curl -s -o nul -w "Frontend (5173):        HTTP %%{http_code}\n" http://127.0.0.1:5173/
echo.
echo Control-token status (should be set:true, length:64):
curl -s http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1/admin/control-token-info
echo.
echo.
echo === Done. Reload http://localhost:5173/ in your browser ===
echo Backend log: type C:\Users\saiyu\AppData\Local\Temp\uvicorn.log
echo Vite log:    type C:\Users\saiyu\AppData\Local\Temp\vite.log
