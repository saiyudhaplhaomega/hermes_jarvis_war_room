#!/usr/bin/env python3
"""Inject window.__CONFIG__ into frontend-react/dist/index.html using the
JARVIS_DASHBOARD_DEV_TOKEN from the project-root .env.local.

This replaces the per-request injection that spa_server.py used to do, so the
SPA can be served by `vite preview` (or any static server) and still send
the dev token with API calls.

Usage:
    python scripts/inject_runtime_config.py
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env.local"
INDEX = ROOT / "frontend-react" / "dist" / "index.html"

if not ENV_FILE.exists():
    print(f"ERROR: {ENV_FILE} not found", file=sys.stderr)
    sys.exit(1)

token = ""
for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
    m = re.match(r"^\s*JARVIS_DASHBOARD_DEV_TOKEN\s*=\s*(.+?)\s*$", line)
    if m:
        token = m.group(1)
        break

if not INDEX.exists():
    print(f"ERROR: {INDEX} not found — run `vite build` first", file=sys.stderr)
    sys.exit(1)

html = INDEX.read_text(encoding="utf-8")
# Remove any prior injection (idempotent)
html = re.sub(
    r'\n?\s*<script>window\.__CONFIG__\s*=.*?</script>',
    "",
    html,
    count=1,
    flags=re.DOTALL,
)

script = (
    '<script>window.__CONFIG__ = { '
    "API_BASE: '/api/plugins/jarvis-dashboard/v1', "
    f"TOKEN: {repr(token)}, "
    "WS_URL: (location.protocol === 'https:' ? 'wss://' : 'ws://') + "
    "location.host + '/api/plugins/jarvis-dashboard/v1/ws' "
    "};</script>"
)
html = html.replace("<head>", f"<head>\n    {script}", 1)
INDEX.write_text(html, encoding="utf-8")
print(f"OK: injected runtime config (token_len={len(token)}) into {INDEX}")
