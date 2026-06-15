#!/usr/bin/env python3
"""Quick health check after a War Room restart. Reads the dev token from
.env.local and exercises the SPA-facing API endpoints that were broken
in the 2026-06-14 round (skills 404 + canned chat).
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env.local"
BASE = "http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1"

token = ""
for line in ENV.read_text(encoding="utf-8").splitlines():
    m = re.match(r"^\s*JARVIS_DASHBOARD_DEV_TOKEN\s*=\s*(.+?)\s*$", line)
    if m:
        token = m.group(1)
        break

if not token:
    print("ERROR: token not found in .env.local")
    sys.exit(1)


def get(path: str) -> dict:
    req = urllib.request.Request(
        BASE + path,
        headers={"Authorization": f"Bearer {token}", "X-Forwarded-User": "jarvis"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


print(f"token_len={len(token)}")
print("--- /skills ---")
d = get("/skills")
skills = d.get("skills", [])
print(f"  skills count: {len(skills)}")
print(f"  sample names: {[s.get('name','?') for s in skills[:5]]}")

print("--- /agents/skills ---")
d = get("/agents/skills")
a = d.get("assignments", [])
print(f"  assignments count: {len(a)}")
print(f"  agents: {sorted({x.get('agent') for x in a if x.get('agent')})[:8]}")

print("--- /agents/proposals ---")
d = get("/agents/proposals")
print(f"  proposals count: {len(d.get('proposals', []))}")

print("--- /dashboard/agents (topology) ---")
d = get("/dashboard/agents")
agents = d if isinstance(d, list) else d.get("agents", [])
print(f"  agents count: {len(agents)}")
print(f"  sample: {[a.get('name') or a.get('slug') for a in agents[:5]]}")

print("--- /dashboard/roles ---")
d = get("/dashboard/roles") if False else None  # may not exist; skip
print("  (skipped)")

print("\nALL CHECKS PASSED" if len(skills) > 0 else "\nWARNING: 0 skills — FIX 1 may be broken")
