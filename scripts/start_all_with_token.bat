@echo off
REM Start both backend and SPA with the SAME dev token
set JARVIS_DASHBOARD_DEV_TOKEN=*** cd /d "C:\Users\saiyu\Desktop\projects\KI_projects\hermes_jarvis_war_room"

REM Start backend in background
start "Backend" cmd /c "set JARVIS_DASHBOARD_DEV_TOKEN=*** && python spa_server.py 8503 frontend-react/dist"

echo Both services starting...
echo Backend: http://127.0.0.1:8502
echo SPA: http://127.0.0.1:8503
pause
