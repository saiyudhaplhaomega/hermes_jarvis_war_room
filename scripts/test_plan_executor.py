"""End-to-end test plan executor for Hermes Jarvis War Room.

Captures real evidence (HTTP responses, file contents, grep output) into
C:/Users/saiyu/AppData/Local/Temp/jarvis_test_evidence/.

NO fabrication. Every assertion shows the actual response or file content.
"""
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import yaml

# ── Setup ──────────────────────────────────────────────────────────────
EVIDENCE = Path(r'C:\Users\saiyu\AppData\Local\Temp\jarvis_test_evidence')
EVIDENCE.mkdir(parents=True, exist_ok=True)
PROJECT = Path(r'C:\Users\saiyu\Desktop\projects\KI_projects\hermes_jarvis_war_room')
API = 'http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1'
APP_DATA = Path(r'C:\Users\saiyu\AppData\Local\hermes')

# Read token from .env.local
token = ''
for line in (PROJECT / '.env.local').read_text(encoding='utf-8').splitlines():
    m = re.match(r'^\s*JARVIS_DASHBOARD_DEV_TOKEN\s*=\s*(.+?)\s*$', line)
    if m:
        token = m.group(1)
        break
assert token, 'Token not found in .env.local'
print(f'[OK] token loaded ({len(token)} chars)')


def auth_headers() -> dict:
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


def http(method: str, path: str, body=None, expect_status=None) -> dict:
    """Make HTTP request, capture status + body + write to evidence file."""
    url = f'{API}{path}'
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, headers=auth_headers(), method=method)
    fname = EVIDENCE / f'{method.lower()}_{path.replace("/", "_").replace("{", "").replace("}", "")}.json'
    result = {'method': method, 'path': path, 'body_in': body, 'timestamp': datetime.now().isoformat()}
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            result['status'] = r.status
            text = r.read().decode('utf-8', errors='replace')
            try:
                result['body'] = json.loads(text)
            except json.JSONDecodeError:
                result['body'] = text[:1000]
    except urllib.error.HTTPError as e:
        result['status'] = e.code
        result['error_body'] = e.read().decode('utf-8', errors='replace')[:500]
    fname.write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
    return result


# ── Test runner ────────────────────────────────────────────────────────
results = []
def record(group, name, passed, evidence_ref, detail):
    status = 'PASS' if passed else 'FAIL'
    results.append({'group': group, 'name': name, 'status': status, 'evidence': evidence_ref, 'detail': detail})
    print(f'  [{status}] {name}: {detail}')


# ╔════════════════════════════════════════════════════════════════════╗
# ║  GROUP A — Backend API                                              ║
# ╚════════════════════════════════════════════════════════════════════╝
print('\n=== GROUP A: BACKEND API ===')

# A1: Create cron job at each of 3 scopes
for scope, name in [('global-hermes', 'A1-global-test'),
                    ('jarvis-war-room', 'A1-warroom-test'),
                    ('hello-world', 'A1-hello-test')]:
    r = http('POST', '/cron/jobs', {
        'name': name, 'agent': 'jarvis', 'prompt': f'test prompt for {scope}',
        'schedule_type': 'interval', 'interval_seconds': 3600,
        'project': scope, 'enabled': True, 'notes': f'A1 test for {scope}'
    })
    ok = r.get('status') == 200 and r.get('body', {}).get('job', {}).get('project') == scope
    record('A', f'A1-create-{scope}', ok, f'POST /cron/jobs (scope={scope})',
           f"status={r.get('status')}, persisted_project={r.get('body', {}).get('job', {}).get('project') if r.get('body') else 'N/A'}")

# A2: Create cron job with empty project
r = http('POST', '/cron/jobs', {
    'name': 'A2-empty-project', 'agent': 'jarvis', 'prompt': 'x',
    'schedule_type': 'interval', 'interval_seconds': 60,
    'project': '', 'enabled': True
})
ok = r.get('status') in (200, 422)  # either accepted or rejected is a valid result
record('A', 'A2-empty-project', ok, 'POST /cron/jobs (project="")',
       f"status={r.get('status')} (expected 200 or 422)")

# A3: List cron jobs
r = http('GET', '/cron/jobs')
ok = r.get('status') == 200 and 'jobs' in r.get('body', {})
job_count = len(r.get('body', {}).get('jobs', [])) if r.get('body') else 0
record('A', 'A3-list-jobs', ok, 'GET /cron/jobs',
       f"status={r.get('status')}, total_jobs={job_count}")

# A4: Create skill import
r = http('POST', '/skills/import', {
    'name': 'A4-test-import-skill', 'summary': 'test skill for A4',
    'source_repo': 'https://github.com/test/test',
    'icon_url': '🧪', 'trust_tier': 'T3',
    'departments': ['jarvis-boss'], 'scope': 'global-hermes'
})
ok = r.get('status') in (200, 409) and 'skill' in r.get('body', {})
record('A', 'A4-skill-import', ok, 'POST /skills/import',
       f"status={r.get('status')}, catalog_size={r.get('body', {}).get('catalog_size', 'N/A') if r.get('body') else 'N/A'}")

# A5: Auth — request without token
url = f'{API}/cron/jobs'
req = urllib.request.Request(url, method='GET')
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        status = r.status
        body = r.read().decode()[:200]
except urllib.error.HTTPError as e:
    status = e.code
    body = e.read().decode()[:200]
ok = status in (401, 403)
record('A', 'A5-no-auth-rejected', ok, 'GET /cron/jobs (no Authorization header)',
       f"status={status} (expected 401 or 403)")


# ╔════════════════════════════════════════════════════════════════════╗
# ║  GROUP B — Persistence                                              ║
# ╚════════════════════════════════════════════════════════════════════╝
print('\n=== GROUP B: PERSISTENCE ===')

# B1: agent_cron_jobs.json
cron_file = APP_DATA / 'state' / 'dashboard' / 'agent_cron_jobs.json'
if cron_file.exists():
    data = json.loads(cron_file.read_text(encoding='utf-8'))
    jobs = data.get('jobs', [])
    scope_counts = {'global-hermes': 0, 'jarvis-war-room': 0, 'hello-world': 0, 'other': 0}
    for j in jobs:
        p = j.get('project', '')
        if p in scope_counts:
            scope_counts[p] += 1
        else:
            scope_counts['other'] += 1
    has_a1_jobs = any('A1-' in j.get('name', '') for j in jobs)
    record('B', 'B1-cron-file-persisted', has_a1_jobs, str(cron_file),
           f"file exists, total_jobs={len(jobs)}, A1 jobs present: {has_a1_jobs}, scope_distribution={scope_counts}")
else:
    record('B', 'B1-cron-file-persisted', False, str(cron_file), 'FILE MISSING')

# B2: agent_skill_catalog.json
catalog_file = APP_DATA / 'state' / 'dashboard' / 'agent_skill_catalog.json'
if catalog_file.exists():
    cat = json.loads(catalog_file.read_text(encoding='utf-8'))
    skills = cat.get('skills', [])
    has_a4 = any(s.get('name') == 'A4-test-import-skill' for s in skills)
    record('B', 'B2-catalog-file-persisted', has_a4, str(catalog_file),
           f"file exists, total_imported={len(skills)}, A4 import present: {has_a4}")
else:
    record('B', 'B2-catalog-file-persisted', False, str(catalog_file), 'FILE MISSING')

# B3: jarvis-boss profile
boss_dir = APP_DATA / 'profiles' / 'jarvis-boss'
config_path = boss_dir / 'config.yaml'
soul_path = boss_dir / 'SOUL.md'
config_exists = config_path.exists()
soul_exists = soul_path.exists()
if config_exists:
    cfg = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    cfg_detail = f"name={cfg.get('name')}, model={cfg.get('model')}, provider={cfg.get('provider')}, status={cfg.get('status')}"
else:
    cfg_detail = 'config.yaml MISSING'
record('B', 'B3-jarvis-boss-profile', config_exists and soul_exists, str(boss_dir),
       f"config={config_exists}, soul={soul_exists}, {cfg_detail}")


# ╔════════════════════════════════════════════════════════════════════╗
# ║  GROUP C — Aggregator (wait 35s, then check)                       ║
# ╚════════════════════════════════════════════════════════════════════╝
print('\n=== GROUP C: AGGREGATOR (waiting for next cycle, may take 30s) ===')

# C1: cache.json contains jarvis-boss with provider=anthropic
cache_file = APP_DATA / 'state' / 'dashboard' / 'cache.json'
import time
last_mtime = 0
if cache_file.exists():
    last_mtime = cache_file.stat().st_mtime

# Force a re-aggregation by waiting up to 35s for new mtime
deadline = time.time() + 35
new_mtime = last_mtime
while time.time() < deadline:
    if cache_file.exists() and cache_file.stat().st_mtime > last_mtime:
        new_mtime = cache_file.stat().st_mtime
        break
    time.sleep(2)

if cache_file.exists():
    cache = json.loads(cache_file.read_text(encoding='utf-8'))
    agents = cache.get('agents', [])
    boss = next((a for a in agents if a.get('name') == 'Jarvis Boss'), None)
    if boss:
        ok = boss.get('provider') == 'anthropic' and boss.get('model') == 'claude-sonnet-4-6'
        record('C', 'C1-jarvis-boss-in-cache', ok, str(cache_file),
               f"provider={boss.get('provider')}, model={boss.get('model')}, status={boss.get('status')}, cache_updated={'yes' if new_mtime > last_mtime else 'no (within 35s window)'}")
    else:
        record('C', 'C1-jarvis-boss-in-cache', False, str(cache_file),
               f"JARVIS BOSS NOT FOUND in {len(agents)} agents. Names: {[a.get('name') for a in agents[:5]]}")
else:
    record('C', 'C1-jarvis-boss-in-cache', False, str(cache_file), 'cache.json MISSING')

# C2: Aggregator covers all profiles (was Codex's earlier concern: 14 vs 7 split)
agents_in_cache = len(cache.get('agents', [])) if cache_file.exists() else 0
record('C', 'C2-aggregator-agents-count', agents_in_cache >= 14, str(cache_file),
       f"agents_in_cache={agents_in_cache} (expected >=14)")


# ╔════════════════════════════════════════════════════════════════════╗
# ║  GROUP E — Code review findings (Codex council)                     ║
# ╚════════════════════════════════════════════════════════════════════╝
print('\n=== GROUP E: CODEX REVIEW FINDINGS ===')

# E1: httpx2 typo
req_file = PROJECT / 'backend' / 'requirements-dev.txt'
if req_file.exists():
    text = req_file.read_text(encoding='utf-8')
    has_httpx2 = 'httpx2' in text
    record('E', 'E1-httpx2-typo', has_httpx2, str(req_file),
           f"confirmed typo: {'httpx2 found' if has_httpx2 else 'no httpx2'}")
else:
    record('E', 'E1-httpx2-typo', False, str(req_file), 'file missing')

# E2: ConnectionProvider not mounted in App.tsx
app_tsx = PROJECT / 'frontend-react' / 'src' / 'App.tsx'
if app_tsx.exists():
    text = app_tsx.read_text(encoding='utf-8')
    mounts_cp = '<ConnectionProvider' in text or 'ConnectionProvider>' in text
    record('E', 'E2-ConnectionProvider-mounted', mounts_cp, str(app_tsx),
           f"ConnectionProvider mounted in App.tsx: {mounts_cp}")
else:
    record('E', 'E2-ConnectionProvider-mounted', False, str(app_tsx), 'App.tsx missing')

# E3: duplicate refreshCatalog in client.ts
client_ts = PROJECT / 'frontend-react' / 'src' / 'api' / 'client.ts'
if client_ts.exists():
    text = client_ts.read_text(encoding='utf-8')
    rc_count = text.count('refreshCatalog:')
    record('E', 'E3-duplicate-refreshCatalog', rc_count > 1, str(client_ts),
           f"refreshCatalog defined {rc_count} times (expected 1)")
else:
    record('E', 'E3-duplicate-refreshCatalog', False, str(client_ts), 'client.ts missing')

# E4: connection cleanup
ctx_ts = PROJECT / 'frontend-react' / 'src' / 'contexts' / 'ConnectionContext.tsx'
if ctx_ts.exists():
    text = ctx_ts.read_text(encoding='utf-8')
    has_cleanup = 'useEffect' in text and 'return ()' in text and ('close()' in text or '.close()' in text)
    record('E', 'E4-connection-cleanup', has_cleanup, str(ctx_ts),
           f"EventSource/WebSocket close in cleanup: {has_cleanup}")
else:
    record('E', 'E4-connection-cleanup', False, str(ctx_ts), 'ConnectionContext.tsx missing')


# ╔════════════════════════════════════════════════════════════════════╗
# ║  SUMMARY                                                            ║
# ╚════════════════════════════════════════════════════════════════════╝
print('\n=== SUMMARY ===')
passed = sum(1 for r in results if r['status'] == 'PASS')
failed = sum(1 for r in results if r['status'] == 'FAIL')
print(f'Total: {len(results)}, Passed: {passed}, Failed: {failed}')
if failed:
    print('\nFailed tests:')
    for r in results:
        if r['status'] == 'FAIL':
            print(f"  {r['group']} {r['name']}: {r['detail']}")

# Save summary
summary_file = EVIDENCE / 'summary.json'
summary_file.write_text(json.dumps(results, indent=2), encoding='utf-8')
print(f'\nEvidence saved to: {EVIDENCE}')

sys.exit(0 if failed == 0 else 1)
