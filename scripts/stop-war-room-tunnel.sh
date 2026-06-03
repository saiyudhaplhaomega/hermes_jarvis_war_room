#!/usr/bin/env bash
set -euo pipefail
STATE_DIR="/home/ubuntu/.hermes/profiles/jarvis/plugins/jarvis-dashboard/state"
PID_FILE="$STATE_DIR/cloudflared.pid"
URL_FILE="$STATE_DIR/cloudflared.url"
LOG_FILE="$STATE_DIR/cloudflared.log"
SHUTDOWN_PID_FILE="$STATE_DIR/cloudflared-shutdown.pid"

stopped=0
if [ -f "$PID_FILE" ]; then
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
    stopped=1
  fi
fi

if [ -f "$SHUTDOWN_PID_FILE" ]; then
  spid="$(cat "$SHUTDOWN_PID_FILE" 2>/dev/null || true)"
  if [ -n "${spid:-}" ] && kill -0 "$spid" 2>/dev/null; then
    kill "$spid" 2>/dev/null || true
  fi
fi

rm -f "$PID_FILE" "$URL_FILE" "$SHUTDOWN_PID_FILE"
if [ "$stopped" = "1" ]; then
  echo "War Room tunnel stopped."
else
  echo "No active War Room tunnel found."
fi
if [ -f "$LOG_FILE" ]; then
  echo "Log kept at: $LOG_FILE"
fi
