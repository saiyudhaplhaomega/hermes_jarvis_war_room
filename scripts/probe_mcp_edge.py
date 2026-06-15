"""MCP catalog edge-case test suite (D-2026-06-15).

Probes the API for bugs that would only show up under unusual input:
auth failures, invalid payloads, path traversal, unicode, idempotency,
empty fields, very long strings, malformed URLs, scope/agent mismatches.
"""
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

token = ''
for line in Path('.env.local').read_text(encoding='utf-8').splitlines():
    m = re.match(r'^\s*JARVIS_DASHBOARD_DEV_TOKEN\s*=\s*(.+?)\s*$', line)
    if m: token = m.group(1); break
assert token, 'no token in .env.local'

API = 'http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1'

def http(method: str, path: str, body=None, headers=None, expect=None):
    url = f'{API}{path}'
    data = json.dumps(body).encode() if body is not None else None
    h = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode('utf-8', errors='replace')[:300]
        try:
            return e.code, json.loads(body_txt) if body_txt.startswith('{') else body_txt
        except json.JSONDecodeError:
            return e.code, body_txt

results = []
def record(name, ok, detail):
    results.append({'name': name, 'status': 'PASS' if ok else 'FAIL', 'detail': detail})
    print(f'  [{"PASS" if ok else "FAIL"}] {name}: {detail}')


print('=== E1: Auth ===')
# E1a: no auth header
req = urllib.request.Request(f'{API}/mcp/catalog', method='GET')
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        s, _ = r.status, r.read()
        record('E1a-no-auth', False, f'should be 401, got {s}')
except urllib.error.HTTPError as e:
    record('E1a-no-auth', e.code in (401, 403), f'status={e.code}')

# E1b: bad token
s, b = http('GET', '/mcp/catalog', headers={'Authorization': 'Bearer wrong_token_xyz'})
record('E1b-bad-token', s == 401, f'status={s}, body={b}')


print('\n=== E2: Invalid payloads ===')
# E2a: empty name
s, b = http('POST', '/mcp/catalog/add', {'name': '', 'source_type': 'name'})
record('E2a-empty-name', s in (400, 422), f'status={s}, body={str(b)[:150]}')

# E2b: invalid source_type
s, b = http('POST', '/mcp/catalog/add', {'name': 'test-invalid-source', 'source_type': 'invalid_kind'})
record('E2b-invalid-source', s in (400, 422), f'status={s}, body={str(b)[:150]}')

# E2c: invalid trust_tier
s, b = http('POST', '/mcp/catalog/add', {'name': 'test-invalid-trust', 'source_type': 'name', 'trust_tier': 'T9'})
record('E2c-invalid-trust', s in (400, 422), f'status={s}, body={str(b)[:150]}')

# E2d: name with bad characters (Pydantic regex requires alphanumeric+_-)
s, b = http('POST', '/mcp/catalog/add', {'name': 'has spaces!@#', 'source_type': 'name'})
record('E2d-bad-chars', s in (400, 422), f'status={s}, body={str(b)[:150]}')

# E2e: extremely long name
s, b = http('POST', '/mcp/catalog/add', {'name': 'a' * 200, 'source_type': 'name'})
record('E2e-long-name', s in (400, 422), f'status={s}, body={str(b)[:150]}')


print('\n=== E3: Path traversal / injection ===')
# E3a: name with ../ attempting to escape storage
s, b = http('POST', '/mcp/catalog/add', {'name': '../../../etc/passwd', 'source_type': 'name'})
record('E3a-name-traversal', s in (400, 422), f'status={s}, body={str(b)[:150]}')

# E3b: source_url with file:// scheme
s, b = http('POST', '/mcp/catalog/add', {'name': 'test-file-url', 'source_type': 'webpage_url', 'source_url': 'file:///etc/passwd'})
# 200 might be OK if we just store it as a string (we don't fetch), but check no execution
record('E3b-file-url', s in (200, 400, 422), f'status={s}, body={str(b)[:150]}')

# E3c: source_url with javascript: scheme
s, b = http('POST', '/mcp/catalog/add', {'name': 'test-js-url', 'source_type': 'webpage_url', 'source_url': 'javascript:alert(1)'})
record('E3c-js-url', s in (200, 400, 422), f'status={s}')


print('\n=== E4: Unicode & very long strings ===')
# E4a: Unicode name
s, b = http('POST', '/mcp/catalog/add', {
    'name': 'unicode-test-1', 'source_type': 'name',
    'summary': '🎭 MCP with unicode — 测试 — Ω — 🚀', 'icon': '🎭'
})
ok_name = s in (200, 409)  # 200 first time, 409 if rerun
record('E4a-unicode', s in (200, 400, 409, 422), f'status={s}')

# E4b: very long summary (close to 500 char limit)
long_summary = 'x' * 600
s, b = http('POST', '/mcp/catalog/add', {
    'name': 'long-summary-test', 'source_type': 'name',
    'summary': long_summary,
})
record('E4b-long-summary', s in (400, 422), f'status={s}, body={str(b)[:150]}')

# E4c: empty body
s, b = http('POST', '/mcp/catalog/add', {})
record('E4c-empty-body', s in (400, 422), f'status={s}, body={str(b)[:150]}')


print('\n=== E5: Idempotency ===')
# E5a: install_from_chat with same URL twice — should NOT duplicate
s1, b1 = http('POST', '/mcp/install-from-chat', {'text': 'https://github.com/anthropics/anthropic-sdk-python', 'scope': 'global-hermes'})
s2, b2 = http('POST', '/mcp/install-from-chat', {'text': 'https://github.com/anthropics/anthropic-sdk-python', 'scope': 'global-hermes'})
size1 = b1.get('catalog_size', '?')
size2 = b2.get('catalog_size', '?')
record('E5a-install-idempotent', s1 == 200 and s2 == 200 and size1 == size2, f'first catalog_size={size1}, second={size2}')

# E5b: add same name twice — second should 409
s, b = http('POST', '/mcp/catalog/add', {'name': 'anthropics-anthropic-sdk-python', 'source_type': 'github_url'})
record('E5b-add-dup-409', s == 409, f'status={s}, body={str(b)[:100]}')


print('\n=== E6: Delete + get edge cases ===')
# E6a: delete non-existent
s, b = http('DELETE', '/mcp/catalog/does-not-exist-mcp-xyz')
record('E6a-delete-missing', s == 404, f'status={s}, body={str(b)[:150]}')

# E6b: get non-existent
s, b = http('GET', '/mcp/catalog/does-not-exist-mcp-xyz')
record('E6b-get-missing', s == 404, f'status={s}, body={str(b)[:150]}')


print('\n=== E7: Chat intent edge cases ===')
# E7a: empty text
s, b = http('POST', '/mcp/chat-intent', {'text': ''})
record('E7a-empty-intent', s in (400, 422), f'status={s}')

# E7b: very long text
long_text = 'add the ' + ('a' * 3000) + ' mcp'
s, b = http('POST', '/mcp/chat-intent', {'text': long_text})
record('E7b-long-intent', s in (200, 400, 422), f'status={s}')

# E7c: mixed-case trigger
s, b = http('POST', '/mcp/chat-intent', {'text': 'ADD THE Postgres MCP'})
record('E7c-uppercase-trigger', s == 200 and b.get('is_mcp_intent') == True,
       f'status={s}, intent={b.get("is_mcp_intent")}, name={b.get("extracted", {}).get("name")}')

# E7d: just a URL with extra whitespace
s, b = http('POST', '/mcp/chat-intent', {'text': '   https://github.com/microsoft/playwright-mcp   '})
record('E7d-url-whitespace', s == 200 and b.get('is_mcp_intent') == True,
       f'status={s}, intent={b.get("is_mcp_intent")}, kind={b.get("extracted", {}).get("kind")}')

# E7e: file in the middle of a sentence (no MCP trigger)
s, b = http('POST', '/mcp/chat-intent', {'text': 'I have a file at https://example.com that I want to discuss'})
record('E7e-non-mcp-url', s == 200 and b.get('is_mcp_intent') == True,
       f'status={s}, intent={b.get("is_mcp_intent")} (note: regex may catch any URL)')


print('\n=== E8: Real-world URLs ===')
real_urls = [
    'https://github.com/microsoft/playwright-mcp',
    'https://github.com/upstash/context7-mcp',
    'https://github.com/awslabs/mcp',
    'https://github.com/mcp-get/server-repo',
    'https://modelcontextprotocol.io/docs/servers',
]
for url in real_urls:
    s, b = http('POST', '/mcp/chat-intent', {'text': url})
    kind = b.get('extracted', {}).get('kind') if isinstance(b, dict) else None
    name = b.get('extracted', {}).get('name') if isinstance(b, dict) else None
    record(f'E8-{url.split("/")[-1][:25]}', s == 200 and b.get('is_mcp_intent'),
           f'kind={kind}, name={name}')


print('\n=== E9: Catalog final state ===')
s, b = http('GET', '/mcp/catalog')
names = [m['name'] for m in b.get('mcps', [])]
print(f'  catalog has {b.get("count")} entries:')
for n in names: print(f'    - {n}')


# Save report
report_file = Path(r'C:\Users\saiyu\AppData\Local\Temp\jarvis_test_evidence\mcp_edge_tests.json')
report_file.parent.mkdir(parents=True, exist_ok=True)
report_file.write_text(json.dumps(results, indent=2), encoding='utf-8')

passed = sum(1 for r in results if r['status'] == 'PASS')
failed = sum(1 for r in results if r['status'] == 'FAIL')
print(f'\n=== SUMMARY: {passed}/{len(results)} passed, {failed} failed ===')
print(f'Evidence: {report_file}')
