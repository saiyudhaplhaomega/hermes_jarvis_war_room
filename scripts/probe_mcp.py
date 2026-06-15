"""Smoke test the MCP catalog endpoints."""
import json
import re
import urllib.request
from pathlib import Path

token = ''
for line in Path('.env.local').read_text(encoding='utf-8').splitlines():
    m = re.match(r'^\s*JARVIS_DASHBOARD_DEV_TOKEN\s*=\s*(.+?)\s*$', line)
    if m: token = m.group(1); break

H = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

def req(method, path, body=None):
    url = f'http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1{path}'
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers=H, method=method)
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

# 1. List (empty)
print('=== 1. List catalog (initially empty) ===')
print(req('GET', '/mcp/catalog'))

# 2. Add playwright-mcp via GitHub URL
print('\n=== 2. Add via catalog/add (GitHub URL) ===')
print(req('POST', '/mcp/catalog/add', {
    'name': 'microsoft-playwright-mcp',
    'summary': 'Playwright MCP by Microsoft — browser automation for agents',
    'description': 'An MCP server that lets AI agents control a real browser',
    'icon': '🎭',
    'source_type': 'github_url',
    'source_url': 'https://github.com/microsoft/playwright-mcp',
    'install_command': 'npx -y @microsoft/playwright-mcp',
    'transport': 'stdio',
    'scope': 'global-hermes',
    'trust_tier': 'T1',
}))

# 3. Add via webpage URL
print('\n=== 3. Add webpage URL ===')
print(req('POST', '/mcp/catalog/add', {
    'name': 'mcp-everything',
    'summary': 'MCP everything server from modelcontextprotocol.io',
    'source_type': 'webpage_url',
    'source_url': 'https://modelcontextprotocol.io/docs/servers/everything',
    'transport': 'stdio',
    'scope': 'jarvis-war-room',
}))

# 4. Chat intent: GitHub URL
print('\n=== 4. Chat intent: GitHub URL ===')
print(req('POST', '/mcp/chat-intent', {'text': 'https://github.com/anthropics/anthropic-sdk-python'}))

# 5. Chat intent: phrase
print('\n=== 5. Chat intent: phrase ===')
print(req('POST', '/mcp/chat-intent', {'text': 'add the filesystem MCP'}))

# 6. Chat intent: no signal
print('\n=== 6. Chat intent: no signal ===')
print(req('POST', '/mcp/chat-intent', {'text': 'what is the weather today?'}))

# 7. Install from chat: GitHub URL
print('\n=== 7. Install from chat: GitHub URL ===')
print(req('POST', '/mcp/install-from-chat', {
    'text': 'https://github.com/microsoft/playwright-mcp',
    'scope': 'jarvis-war-room',
    'assign_to': ['jarvis-frontend'],
}))

# 8. Install from chat: phrase
print('\n=== 8. Install from chat: phrase ===')
print(req('POST', '/mcp/install-from-chat', {
    'text': 'add the filesystem MCP',
    'scope': 'global-hermes',
}))

# 9. List (should have all 3 + 2 from chat)
print('\n=== 9. List catalog (final) ===')
status, body = req('GET', '/mcp/catalog')
print(f'status={status}, count={body.get("count")}')
for m in body.get('mcps', []):
    print(f"  - {m['name']} ({m['source_type']}, {m['scope']}) — {m['install_command'] or '(no command)'}")

# 10. Delete one
print('\n=== 10. Delete mcp-everything ===')
print(req('DELETE', '/mcp/catalog/mcp-everything'))

# 11. Get one
print('\n=== 11. Get one ===')
print(req('GET', '/mcp/catalog/microsoft-playwright-mcp'))

# 12. Duplicate add (should 409)
print('\n=== 12. Duplicate add (should 409) ===')
print(req('POST', '/mcp/catalog/add', {'name': 'microsoft-playwright-mcp', 'source_type': 'name'}))
