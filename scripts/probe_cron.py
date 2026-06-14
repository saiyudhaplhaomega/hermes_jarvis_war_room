#!/usr/bin/env python3
"""Probe the new Agent Cron Jobs endpoints end-to-end."""
import json
import re
import urllib.request
from pathlib import Path

token = ''
for line in Path('.env.local').read_text(encoding='utf-8').splitlines():
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
        return e.code, e.read().decode('utf-8', errors='replace')[:200]
    except Exception as e:
        return 0, str(e)

print('=== 1. List jobs (empty) ===')
code, body = http('GET', '/cron/jobs')
print(f'  GET /cron/jobs: {code} count={body.get("count") if isinstance(body, dict) else "?"}')

print()
print('=== 2. Create cron job (5-field cron) ===')
job1 = {
    'name': 'nightly-research-sweep',
    'agent': 'jarvis-boss',
    'prompt': 'sweep the council research docs and surface anything unaddressed',
    'schedule_type': 'cron',
    'cron_expression': '0 9 * * 1-5',
    'project': 'hello-world',
    'enabled': True,
    'notes': 'weekday morning routine',
}
code, body = http('POST', '/cron/jobs', job1)
print(f'  POST /cron/jobs: {code} created={body.get("created") if isinstance(body, dict) else "?"}')
job1_id = body.get('created') if isinstance(body, dict) else None

print()
print('=== 3. Create interval job (every 30 sec) ===')
job2 = {
    'name': 'every-30s-heartbeat',
    'agent': 'jarvis-frontend',
    'prompt': 'check for frontend build errors in the latest run',
    'schedule_type': 'interval',
    'interval_seconds': 30,
    'project': 'hello-world',
    'enabled': True,
}
code, body = http('POST', '/cron/jobs', job2)
print(f'  POST /cron/jobs: {code} created={body.get("created") if isinstance(body, dict) else "?"}')
job2_id = body.get('created') if isinstance(body, dict) else None

print()
print('=== 4. Create one_shot job (in 60 sec) ===')
from datetime import datetime, timezone, timedelta
job3 = {
    'name': 'kickoff-meeting',
    'agent': 'jarvis-boss',
    'prompt': 'send the kickoff agenda to all leads',
    'schedule_type': 'one_shot',
    'run_at': (datetime.now(timezone.utc) + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'project': 'hello-world',
    'enabled': True,
}
code, body = http('POST', '/cron/jobs', job3)
print(f'  POST /cron/jobs: {code} created={body.get("created") if isinstance(body, dict) else "?"}')

print()
print('=== 5. List jobs (should have 3) ===')
code, body = http('GET', '/cron/jobs')
if isinstance(body, dict):
    print(f'  GET /cron/jobs: {code} count={body["count"]}')
    for j in body['jobs']:
        print(f'    - {j["name"]} [{j["schedule_type"]}] agent={j["agent"]} enabled={j["enabled"]}')

print()
print('=== 6. PATCH (disable the interval one) ===')
if job2_id:
    code, body = http('PATCH', f'/cron/jobs/{job2_id}', {'enabled': False})
    print(f'  PATCH /cron/jobs/{job2_id}: {code} enabled={body.get("job", {}).get("enabled") if isinstance(body, dict) else "?"}')

print()
print('=== 7. Run-now the cron one ===')
if job1_id:
    code, body = http('POST', f'/cron/jobs/{job1_id}/run', {})
    print(f'  POST .../run: {code} dispatched={body.get("dispatched") if isinstance(body, dict) else "?"} run_count={body.get("job", {}).get("run_count") if isinstance(body, dict) else "?"}')

print()
print('=== 8. Validation: bad cron expression rejected ===')
bad = {
    'name': 'bad-cron',
    'agent': 'jarvis-boss',
    'prompt': 'x',
    'schedule_type': 'cron',
    'cron_expression': 'not a cron',
}
code, body = http('POST', '/cron/jobs', bad)
print(f'  POST /cron/jobs: {code} (expect 422) {str(body)[:120]}')

print()
print('=== 9. Delete the interval job ===')
if job2_id:
    code, body = http('DELETE', f'/cron/jobs/{job2_id}')
    print(f'  DELETE /cron/jobs/{job2_id}: {code} remaining={body.get("remaining") if isinstance(body, dict) else "?"}')

print()
print('=== 10. Final list ===')
code, body = http('GET', '/cron/jobs')
if isinstance(body, dict):
    print(f'  GET /cron/jobs: {code} count={body["count"]}')
