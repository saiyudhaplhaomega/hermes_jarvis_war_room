#!/bin/bash
# Dashboard service starter. Edit the 2 values below, then run.
#   bash scripts/start_dashboard_services.sh
#
# It will:
#   1. Export the 2 env vars in this shell
#   2. Write frontend-react/.env.local with the dev token
#   3. Start uvicorn (backend) on port 8502 in the background
#   4. Start npm run dev (frontend) on port 5173 in the background
#   5. Wait, then verify both are up

set -e
cd "C:/Users/saiyu/Desktop/projects/KI_projects/hermes_jarvis_war_room"

# ===== EDIT THESE 2 LINES =====
# Paste the values from set_dashboard_secrets.sh output:
#   JARVIS_DASHBOARD_DEV_TOKEN=<dev token, length ~43>
#   JARVIS_CONTROL_TOKEN_SECRET=<ctrl secret, length 64>
export JARVIS_DASHBOARD_DEV_TOKEN="PASTE_DEV_TOKEN_HERE"
export JARVIS_CONTROL_TOKEN_SECRET="PASTE_CTRL_SECRET_HERE"
# ==============================

# Validate
if [[ "$JARVIS_DASHBOARD_DEV_TOKEN" == "PASTE_DEV_TOKEN_HERE" ]] || [[ "$JARVIS_CONTROL_TOKEN_SECRET" == "PASTE_CTRL_SECRET_HERE" ]]; then
    echo "ERROR: Edit scripts/start_dashboard_services.sh and paste the 2 secrets from set_dashboard_secrets.sh output"
    exit 1
fi

echo "JARVIS_DASHBOARD_DEV_TOKEN set, length=${#JARVIS_DASHBOARD_DEV_TOKEN}"
echo "JARVIS_CONTROL_TOKEN_SECRET set, length=${#JARVIS_CONTROL_TOKEN_SECRET}"

# Write .env.local for Vite
cat > frontend-react/.env.local << EOF
# Vite env - auto-loaded by Vite on start. Local dev only.
VITE_API_BASE=/api/plugins/jarvis-dashboard/v1
VITE_TOKEN=$JARVI...echo "frontend-react/.env.local written"
sed -E 's|VITE_TOKEN=.*|VITE_TOKEN=*** MASKED *** (length '"$(awk -F= '/VITE_TOKEN=/{print length($2)}' frontend-react/.env.local)"')|' frontend-react/.env.local

# Kill any old processes
echo ""
echo "=== Killing any old processes on 8502 / 5173 ==="
for port in 8502 5173; do
    fuser -k $port/tcp 2>/dev/null && echo "killed process on $port" || echo "nothing on $port"
done
sleep 2

# Start the backend
echo ""
echo "=== Starting FastAPI backend on port 8502 ==="
cd "C:/Users/saiyu/Desktop/projects/KI_projects/hermes_jarvis_war_room"
nohup python -m uvicorn backend.server:app --host 127.0.0.1 --port 8502 > /tmp/uvicorn.log 2>&1 &
UVICORN_PID=$!
echo "uvicorn PID: $UVICORN_PID"

# Start the Vite dev server
echo ""
echo "=== Starting Vite dev server on port 5173 ==="
cd frontend-react
nohup npm run dev > /tmp/vite.log 2>&1 &
VITE_PID=$!
echo "vite PID: $VITE_PID"
cd ..

# Wait for both to be ready
echo ""
echo "=== Waiting 8 seconds for both to bind ==="
sleep 8

# Verify
echo ""
echo "=== Verification ==="
curl -s -o /dev/null -w "Backend (8502) health: HTTP %{http_code}\n" http://127.0.0.1:8502/api/plugins/jarvis-dashboard/health
curl -s -o /dev/null -w "Frontend (5173): HTTP %{http_code}\n" http://127.0.0.1:5173/
echo ""
echo "Control-token status (should be set:true, length:64):"
curl -s http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1/admin/control-token-info
echo ""
echo ""
echo "Reload the dashboard: http://localhost:5173/"
echo "Backend logs: tail -f /tmp/uvicorn.log"
echo "Vite logs:    tail -f /tmp/vite.log"
