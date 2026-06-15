#!/bin/bash
# Sets the 2 env vars in THIS shell, then writes frontend-react/.env.local
# with the real dev token. Run this ONCE in your terminal:
#
#   bash scripts/fix_dashboard_all_in_one.sh
#
# It will leave the env vars set in the current shell so subsequent commands
# (uvicorn, npm run dev) can use them.

set -e

cd "C:/Users/saiyu/Desktop/projects/KI_projects/hermes_jarvis_war_room" || cd "$(dirname "$0")/.."

# Step 1: Set the 2 secrets in this shell's env
if [ -z "$JARVIS_DASHBOARD_DEV_TOKEN" ]; then
    export JARVIS_DASHBOARD_DEV_TOKEN=*** -c "import secrets; print(secrets.token_urlsafe(32))")
fi
if [ -z "$JARVIS_CONTROL_TOKEN_SECRET" ]; then
    export JARVIS_CONTROL_TOKEN_SECRET=*** -c "import secrets; print(secrets.token_urlsafe(48))")
fi

echo "JARVIS_DASHBOARD_DEV_TOKEN set, length=${#JARVIS_DASHBOARD_DEV_TOKEN}"
echo "  Token: $JARVIS_DASHBOARD_DEV_TOKEN"
echo "JARVIS_CONTROL_TOKEN_SECRET set, length=${#JARVIS_CONTROL_TOKEN_SECRET}"
echo "  (not shown for safety)"
echo ""

# Step 2: Run the python script that reads from env and writes .env.local
python /c/Users/saiyu/AppData/Local/Temp/write_env.py
