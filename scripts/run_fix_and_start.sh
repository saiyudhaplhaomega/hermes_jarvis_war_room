#!/bin/bash
# Run this from the same shell where you ran set_dashboard_secrets.sh.
# Or run it standalone and it will source the secrets itself.

set -e
cd "C:/Users/saiyu/Desktop/projects/KI_projects/hermes_jarvis_war_room"

# 1. Get the secrets
if [ -z "$JARVIS_DASHBOARD_DEV_TOKEN" ] || [ -z "$JARVIS_CONTROL_TOKEN_SECRET" ]; then
    echo "Env vars not set. Sourcing set_dashboard_secrets.sh..."
    set +e
    source ./scripts/set_dashboard_secrets.sh > /tmp/secrets_source.log 2>&1
    set -e
    # Source may print the dev token to stdout, redirect to log
    if [ -z "$JARVIS_DASHBOARD_DEV_TOKEN" ] || [ -z "$JARVIS_CONTROL_TOKEN_SECRET" ]; then
        echo "ERROR: still no env vars after sourcing. Check /tmp/secrets_source.log"
        cat /tmp/secrets_source.log
        exit 1
    fi
fi

echo "JARVIS_DASHBOARD_DEV_TOKEN length=${#JARVIS_DASHBOARD_DEV_TOKEN}"
echo "JARVIS_CONTROL_TOKEN_SECRET length=${#JARVIS_CONTROL_TOKEN_SECRET}"

# 2. Write the secrets file using a heredoc with env-var interpolation
#    The variables are referenced as $XXX directly so bash expands them
SECRETS_FILE="$HOME/jarvis_dashboard_secrets.txt"
cat > "$SECRETS_FILE" << EOF_OUTER
JARVIS_DASHBOARD_DEV_TOKEN=$JARVI...ARVIS_CONTROL_TOKEN_SECRET=$JARVIS_CONTROL_TOKEN_SECRET
EOF_OUTER

echo
echo "Wrote $SECRETS_FILE"
ls -la "$SECRETS_FILE"

# 3. Verify the file content has the right lengths
DEV_LEN=$(awk -F= '/^JARVIS_DASHBOARD_DEV_TOKEN=/{print length($2)}' "$SECRETS_FILE")
CTRL_LEN=$(awk -F= '/^JARVIS_CONTROL_TOKEN_SECRET=/{print length($2)}' "$SECRETS_FILE")
echo "File content lengths: dev=$DEV_LEN, ctrl=$CTRL_LEN"
if [ "$DEV_LEN" -lt 30 ] || [ "$CTRL_LEN" -lt 60 ]; then
    echo "ERROR: secrets file has wrong lengths"
    exit 1
fi

# 4. Run the start script
echo
echo "=== Running scripts/start_dashboard.py ==="
python scripts/start_dashboard.py
