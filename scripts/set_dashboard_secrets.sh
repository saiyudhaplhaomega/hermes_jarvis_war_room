#!/bin/bash
# Set the 2 env vars the dashboard needs. Run this in your terminal,
# then tell me "secrets are set, proceed" and I do the fix.
#
# These are dev-mode secrets, NOT for production. The HMAC control-token
# secret gates the backend's CONTROL message flow (per r59 R-PERM-1).
# The dev token is what Vite injects as Bearer auth for the React app.

# Step 1: Generate strong random secrets
export JARVIS_CONTROL_TOKEN_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
export JARVIS_DASHBOARD_DEV_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Step 2: Verify both are set
echo "JARVIS_CONTROL_TOKEN_SECRET set: $([ -n \"$JARVIS_CONTROL_TOKEN_SECRET\" ] && echo yes || echo no)"
echo "JARVIS_DASHBOARD_DEV_TOKEN set:   $([ -n \"$JARVIS_DASHBOARD_DEV_TOKEN\" ] && echo yes || echo no)"

# Step 3: Print the dev token (so you can paste it into frontend-react/.env.local if I need you to)
# The HMAC secret NEVER gets printed -- it stays in this shell's env only.
echo ""
echo "JARVIS_DASHBOARD_DEV_TOKEN (safe to share with frontend):"
echo "  $JARVIS_DASHBOARD_DEV_TOKEN"
echo ""
echo "JARVIS_CONTROL_TOKEN_SECRET (KEEP IN THIS SHELL ONLY):"
echo "  (set, length=${#JARVIS_CONTROL_TOKEN_SECRET}, not shown for safety)"
echo ""
echo "Now tell me: 'secrets are set, proceed' and I'll:"
echo "  1. Restart the FastAPI backend (port 8502) with the HMAC secret"
echo "  2. Restart the Vite dev server (port 5173) with the dev token"
echo "  3. Reload the dashboard and verify the panels populate"
