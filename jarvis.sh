#!/usr/bin/env bash
# Jarvis War Room — POSIX launcher (works in git-bash on Windows too).
# Closes cleanly with Ctrl+C; both servers are killed.
set -e
cd "$(dirname "$0")"
exec ./.venv/Scripts/python.exe jarvis_war_room.py "$@"
