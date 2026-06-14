#!/usr/bin/env python3
"""Probe the new skill-catalog + import endpoints."""
import json
import re
import urllib.request
from pathlib import Path

ENV = Path('.env.local')
token = ''
for line in ENV.read_text(encoding='utf-8').splitlines():
    m = re.match(r'^\s*JARVIS_DASHBOARD_DEV_TOKEN\s*=\s*(.+?)\s*$', line)
    if m: token = m.group(1); break

H = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
BASE = 'http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1'

def http(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f'{BASE}{path}', data=data, method=method, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')
    except Exception as e:
        return 0, str(e)

print('=== Existing endpoints (should now work) ===')
for path in ['/catalog', '/catalog/refresh', '/catalog/by-department/jarvis-frontend',
             '/agents/jarvis-frontend/skills-by-project?project=hello-world']:
    code, body = http('GET', path)
    if code == 200:
        if isinstance(body, dict):
            if 'skills' in body:
                print(f'  GET {path}: {code} ({len(body["skills"])} skills)')
            elif 'count' in body:
                print(f'  GET {path}: {code} (count={body["count"]})')
            else:
                print(f'  GET {path}: {code}')
    else:
        print(f'  GET {path}: {code} {str(body)[:120]}')

print()
print('=== Import a skill ===')
import_payload = {
    "name": "code-review-assistant",
    "summary": "Reviews pull requests for style, security, and test coverage. Posts inline comments and a summary verdict.",
    "description": "Full long description here.",
    "source_repo": "https://github.com/octocat/skills",
    "source_path": "skills/code-review-assistant/SKILL.md",
    "icon_url": "🔍",
    "trust_tier": "T2",
    "departments": ["jarvis-qa-lead", "jarvis-engineering-lead"],
    "category": "user-imported",
}
code, body = http('POST', '/skills/import', import_payload)
print(f'  POST /skills/import: {code} catalog_size={body.get("catalog_size") if isinstance(body, dict) else "?"}')

print()
print('=== Import a 2nd skill (for orchestrator) ===')
import_payload2 = {
    "name": "orchestrator-delegate",
    "summary": "Breaks a goal into subtasks and dispatches them to the right agent based on each agent's role + skills. Tracks progress and reassigns on failure.",
    "source_repo": "https://github.com/saiyu/jarvis-orchestrator",
    "icon_url": "🎯",
    "trust_tier": "T1",
    "departments": ["jarvis-boss", "jarvis-engineering-lead", "jarvis-product-lead"],
    "category": "orchestration",
}
code, body = http('POST', '/skills/import', import_payload2)
print(f'  POST /skills/import: {code} catalog_size={body.get("catalog_size") if isinstance(body, dict) else "?"}')

print()
print('=== List user-imported skills ===')
code, body = http('GET', '/skills/imports')
if isinstance(body, dict):
    print(f'  GET /skills/imports: {code} count={body["count"]}')
    for s in body['skills']:
        print(f'    - {s["name"]} (icon={s.get("icon_url","")!r}, trust={s["trust_tier"]}, depts={s.get("departments",[])})')

print()
print('=== Get full catalog (now includes imports) ===')
code, body = http('GET', '/catalog')
if isinstance(body, dict):
    print(f'  GET /catalog: {code} total={body["summary"]["total_skills"]} by_tier={body["summary"]["by_trust_tier"]}')

print()
print('=== Assign skills to the orchestrator (jarvis-boss) for project hello-world ===')
assign = {
    "agent": "jarvis-boss",
    "project": "hello-world",
    "skills": ["orchestrator-delegate", "code-review-assistant", "agent-scheduling"],
    "notes": "Pinned for project hello-world",
}
code, body = http('POST', '/agents/skills-by-project', assign)
print(f'  POST /agents/skills-by-project: {code} {str(body)[:160]}')

print()
print('=== Read back the assignment ===')
code, body = http('GET', '/agents/jarvis-boss/skills-by-project?project=hello-world')
print(f'  GET ...: {code} {json.dumps(body, indent=2) if isinstance(body, dict) else body}')
