#!/usr/bin/env bash
# Start SPA server with auth token
export JARVIS_DASHBOARD_DEV_TOKEN=***
cd "/c/Users/saiyu/Desktop/projects/KI_projects/hermes_jarvis_war_room"
python spa_server.py 8503 "frontend-react/dist"