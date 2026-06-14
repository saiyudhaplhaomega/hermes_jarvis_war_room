@echo off
REM Jarvis War Room — Windows desktop launcher
REM Double-click this to start the dashboard.
REM Close the window or press Ctrl+C in the terminal to stop.

cd /d "%~dp0"
".venv\Scripts\python.exe" jarvis_war_room.py %*
