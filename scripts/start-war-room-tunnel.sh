#!/usr/bin/env bash
set -euo pipefail
DURATION_MINUTES="${1:-30}"
APP_URL="${WAR_ROOM_LOCAL_URL:-http://127.0.0.1:8503}"
CLOUDFLARED="${CLOUDFLARED_BIN:-/home/ubuntu/bin/cloudflared}"
BASE="/home/ubuntu/.hermes/profiles/jarvis/plugins/jarvis-dashboard"
STATE_DIR="$BASE/state"
PID_FILE="$STATE_DIR/cloudflared.pid"
URL_FILE="$STATE_DIR/cloudflared.url"
LOG_FILE="$STATE_DIR/cloudflared.log"
SHUTDOWN_PID_FILE="$STATE_DIR/cloudflared-shutdown.pid"
STOP_SCRIPT="$BASE/scripts/stop-war-room-tunnel.sh"
mkdir -p "$STATE_DIR"

if ! [[ "$DURATION_MINUTES" =~ ^[0-9]+$ ]]; then
  echo "ERROR: duration must be minutes as an integer" >&2
  exit 2
fi

if [ ! -x "$CLOUDFLARED" ]; then
  if command -v cloudflared >/dev/null 2>&1; then
    CLOUDFLARED="$(command -v cloudflared)"
  else
    echo "ERROR: cloudflared not found" >&2
    exit 3
  fi
fi

# Stop previous tunnel if any.
if [ -x "$STOP_SCRIPT" ]; then
  "$STOP_SCRIPT" >/dev/null 2>&1 || true
fi
: > "$LOG_FILE"
rm -f "$URL_FILE" "$PID_FILE" "$SHUTDOWN_PID_FILE"

"$CLOUDFLARED" tunnel --no-autoupdate --url "$APP_URL" >"$LOG_FILE" 2>&1 &
pid=$!
echo "$pid" > "$PID_FILE"

url=""
for _ in $(seq 1 40); do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "ERROR: cloudflared exited early. Log:" >&2
    tail -80 "$LOG_FILE" >&2 || true
    exit 4
  fi
  url="$(python3 - "$LOG_FILE" <<'PY'
import re, sys
p=sys.argv[1]
try:
    s=open(p, 'r', errors='replace').read()
except FileNotFoundError:
    s=''
urls=re.findall(r'https://[-a-zA-Z0-9.]+\.trycloudflare\.com', s)
print(urls[-1] if urls else '')
PY
)"
  if [ -n "$url" ]; then
    break
  fi
  sleep 0.5
done

if [ -z "$url" ]; then
  echo "ERROR: cloudflared did not emit a trycloudflare URL. Log:" >&2
  tail -120 "$LOG_FILE" >&2 || true
  exit 5
fi

echo "$url" > "$URL_FILE"
(
  sleep "$((DURATION_MINUTES * 60))"
  "$STOP_SCRIPT" >>"$LOG_FILE" 2>&1 || true
) &
echo $! > "$SHUTDOWN_PID_FILE"

printf 'WAR_ROOM_TUNNEL_URL=%s/war-room\n' "$url"
printf 'BASE_TUNNEL_URL=%s\n' "$url"
printf 'EXPIRES_IN_MINUTES=%s\n' "$DURATION_MINUTES"
printf 'PID=%s\n' "$pid"
printf 'LOG=%s\n' "$LOG_FILE"
