#!/usr/bin/env python3
"""Quick probe of the dashboard skill endpoints."""
import re
import sys
import urllib.request
from pathlib import Path

ENV = Path('.env.local')
token = ''
for line in ENV.read_text(encoding='utf-8').splitlines():
    m = re.match(r'^\s*JARVIS_DASHBOARD_DEV_TOKEN\s*=\s*(.+?)\s*$', line)
    if m: token = m.group(1); break

H = {'Authorization': f'Bearer {token}'}

def probe(path):
    try:
        req = urllib.request.Request(f'http://127.0.0.1:8502{path}', headers=H)
        with urllib.request.urlopen(req, timeout=3) as r:
            d = r.read()
            print(f'  {path}: HTTP {r.status} {len(d)} bytes')
    except Exception as e:
        print(f'  {path}: ERROR {e}')

for p in ['/api/plugins/jarvis-dashboard/v1/skills',
         '/api/plugins/jarvis-dashboard/v1/catalog',
         '/api/plugins/jarvis-dashboard/v1/catalog/refresh',
         '/api/plugins/jarvis-dashboard/v1/catalog/by-department/jarvis-frontend',
         '/api/plugins/jarvis-dashboard/v1/agents/skills',
         '/api/plugins/jarvis-dashboard/v1/agents/jarvis-frontend/skills-by-project?project=hello-world',
         '/api/plugins/jarvis-dashboard/v1/agents/proposals',
         '/api/plugins/jarvis-dashboard/v1/agents/removed']:
    probe(p)
