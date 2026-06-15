#!/bin/bash
# All-in-one fix: set secrets, write .env.local, verify, then start the 2 processes.
# Run this ONCE in your terminal:
#   bash scripts/fix_dashboard.sh
#
# It will:
#   1. Set the 2 secrets in this shell's env
#   2. Run the Python script to write .env.local with the real token
#   3. Print verification info
#   4. Then say "ready for restart" so you can re-run the restart commands.

set -e

echo "=== Step 1: Set the 2 secrets in this shell ==="
if [ -z "$JARVIS_CONTROL_TOKEN_SECRET" ]; then
    export JARVIS_CONTROL_TOKEN_SECRET=*** -c "import secrets; print(secrets.token_urlsafe(48))")
    echo "Generated new JARVIS_CONTROL_TOKEN_SECRET (length=${#JARVIS_CONTROL_TOKEN_SECRET})"
else
    echo "JARVIS_CONTROL_TOKEN_SECRET already set (length=${#JARVIS_CONTROL_TOKEN_SECRET})"
fi

if [ -z "$JARVIS_DASHBOARD_DEV_TOKEN" ]; then
    export JARVIS_DASHBOARD_DEV_TOKEN=*** -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "Generated new JARVIS_DASHBOARD_DEV_TOKEN (length=${#JARVIS_DASHBOARD_DEV_TOKEN})"
    echo "  Dev token: $JARVIS_DASHBOARD_DEV_TOKEN"
else
    echo "JARVIS_DASHBOARD_DEV_TOKEN already set (length=${#JARVIS_DASHBOARD_DEV_TOKEN})"
    echo "  Dev token: $JARVIS_DASHBOARD_DEV_TOKEN"
fi

echo ""
echo "=== Step 2: Run the Python script to write .env.local ==="
python /c/Users/saiyu/AppData/Local/Temp/write_env.py

echo ""
echo "=== Step 3: Both env vars are now set in THIS shell ==="
echo "  JARVIS_CONTROL_TOKEN_SECRET: length=${#JARVIS_CONTROL_TOKEN_SECRET}"
echo "  JARVIS_DASHBOARD_DEV_TOKEN:   length=${#JARVIS_DASHBOARD_DEV_TOKEN}"
echo ""
echo "=== Next: the 2 process restarts ==="
echo ""
echo "In THIS terminal (where the env vars are set), I will now run:"
echo "  1. uvicorn backend.server:app --host 127.0.0.1 --port 8502  (in background)"
echo "  2. cd frontend-react && npm run dev  (in background)"
echo ""
echo "After both are up, verify with: curl http://127.0.0.1:8502/api/plugins/jarvis-dashboard/health"
