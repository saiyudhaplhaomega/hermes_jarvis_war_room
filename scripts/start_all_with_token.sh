#!/usr/bin/env bash
# Start backend and SPA with the same dev token (read from .env.local)
set -a
ENV_FILE="/c/Users/saiyu/Desktop/projects/KI_projects/hermes_jarvis_war_room/.env.local"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
fi
set +a
cd "/c/Users/saiyu/Desktop/projects/KI_projects/hermes_jarvis_war_room"
echo "Token length: ${#JARVIS_DASHBOARD_DEV_TOKEN}"
echo "Starting backend on :8502..."
python backend/server.py > /tmp/backend.log 2>&1 &
echo "Starting SPA on :8503..."
python spa_server.py 8503 "frontend-react/dist" > /tmp/spa.log 2>&1 &
sleep 5
echo "=== TOKEN in HTML ==="
curl -s http://127.0.0.1:8503/ | grep TOKEN
echo "=== Backend health ==="
curl -s http://127.0.0.1:8502/api/plugins/jarvis-dashboard/health
echo ""
echo "Done."