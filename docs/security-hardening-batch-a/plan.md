# War Room Security Hardening Batch A — Technical Plan

```yaml
name: war-room-security-hardening-batch-a-plan
status: DRAFT_FOR_SAIYUDH_APPROVAL
created: 2026-06-03T22:31:45+08:00
coding_status: NOT_APPROVED
```

## 1. Stack

- Backend: FastAPI, Starlette middleware, Uvicorn.
- Frontend: React/Vite served by `spa_server.py`, plus legacy static HTML assets.
- Runtime: systemd services on VPS, localhost-bound backend and SPA.
- Auth: current dev token/JWT helpers in `backend/auth/dependencies.py`.
- Logs: journald plus project audit JSONL.
- Deployment target: existing VPS only.

## 2. Architecture

Current flow:

```text
Browser
  -> SPA server on 127.0.0.1:8503
  -> /api/plugins/... proxy
  -> backend on 127.0.0.1:8502
```

Batch A target:

```text
Browser
  -> SPA server injects runtime config without putting token into request URLs
  -> REST fetch sends Authorization header or cookie
  -> WebSocket authenticates through cookie/session/bootstrap path, not query token
  -> backend validates via shared auth helper
  -> logs redact legacy token-like query values
```

No Kubernetes/k3s path is involved.

## 3. Data/Auth Flow

### 3.1 Deployment topology assumption

Batch A assumes the normal browser path is same-origin through `spa_server.py`:

```text
Browser origin: http://127.0.0.1:8503 or approved War Room origin
REST path:      /api/plugins/jarvis-dashboard/v1/...  -> spa_server.py proxy -> 127.0.0.1:8502
WS path:        /api/plugins/jarvis-dashboard/v1/ws   -> same browser host, backend WS route
```

Cookie/session auth is only approved if this same-origin/proxy topology is preserved. If the dashboard is served cross-origin without HTTPS, WS-A must be revisited because browser cookie rules (`SameSite=None; Secure`) would otherwise break or weaken the design.

### 3.2 REST API

Approved target path:

```text
CONFIG.TOKEN -> frontend API client -> Authorization: Bearer *** -> spa_server proxy preserves header -> backend get_current_user()
```

Implementation detail:

- `frontend-react/src/api/client.ts` removes token query construction.
- All `get()` and `post()` calls send `Authorization: Bearer ${TOKEN}` when `TOKEN` exists.
- `spa_server.py` already preserves `Authorization`; smoke tests must verify this path.
- `backend/auth/dependencies.py` reads bearer token before considering legacy query token.

Compatibility path:

```text
?token=... -> backend get_current_user() -> accepted only behind an explicit compatibility flag or documented deprecation window
```

### 3.3 WebSocket

Browser WebSocket constructors cannot set arbitrary `Authorization` headers. Therefore the implementation must choose one of these before coding:

Option WS-A, recommended and now specified:

```text
1. Browser sends POST /api/plugins/jarvis-dashboard/v1/auth/session
   with Authorization: Bearer ***.
2. Backend validates token and sets cookie:
   jarvis-dashboard-token=<signed-or-existing-token>;
   HttpOnly; SameSite=Lax; Path=/api/plugins/jarvis-dashboard; Max-Age=3600
3. Browser opens WebSocket to CONFIG.WS_URL with no query string.
4. Backend reads cookie during WS handshake and verifies before accept.
5. Missing/invalid cookie closes with policy/auth code before any useful session behavior.
```

WS-A constraints:

- Requires same-origin or same-site deployment through `spa_server.py`.
- Does not require `SameSite=None; Secure` for the current localhost/VPN-style origin.
- Does not add persistent server-side session storage in Batch A; cookie value is the existing validated token or a signed wrapper if already available.
- CSRF risk is bounded because the session endpoint requires Authorization bearer token; normal API mutations still require auth. Future multi-user/public exposure needs a CSRF review.

Option WS-B:

```text
SPA uses first WS message {type:"auth", token:"..."}; backend accepts then closes quickly if auth fails
```

Pros: smaller change.
Cons: token still crosses WS payload and connection is accepted before auth; less ideal.

Option WS-C:

```text
Keep ?token= as temporary fallback only
```

Pros: lowest change.
Cons: does not solve the primary finding; not acceptable as final Batch A outcome.

Query-token fallback rule:

- Default target is fallback disabled for normal frontend paths.
- If Saiyudh asks to keep legacy support, fallback must be controlled by a named env flag, logged as deprecated, redacted, and removed no later than Batch B security hardening or 2026-06-17, whichever comes first.

Session expiry rule:

- WS-A cookie Max-Age is 3600 seconds.
- Active WebSocket connections must treat expired/invalid auth as closed, not silently trusted forever.
- Backend closes with an auth/policy close code; frontend returns to auth bootstrap/reconnect path.

Plan assumes WS-A unless Saiyudh says otherwise.

## 4. Files

### Backend

- Modify: `backend/auth/dependencies.py`
  - Add `get_bearer_token(request)` support.
  - Add cookie/session token support for HTTP and WS.
  - Preserve compare_digest.

- Modify: `backend/server.py`
  - Tighten CORS origins.
  - Add `/ready` endpoint.
  - Change WS endpoint to use new auth helper indirectly via manager.
  - Add `access_log=False` to direct `uvicorn.run()`.

- Modify: `backend/core/websocket.py`
  - Stop using query token as primary auth.
  - Validate cookie/session or explicit approved auth mode before `accept()`.
  - Keep query-token fallback only if explicitly approved.

- Possibly create: `backend/api/auth.py`
  - If WS-A selected, add session bootstrap endpoint.

- Possibly modify: `backend/api/__init__.py`
  - Only if router registration requires it.

### Frontend

- Modify: `frontend-react/src/api/client.ts`
  - Stop constructing `?token=${TOKEN}` URLs.
  - Add `Authorization: Bearer ${TOKEN}` or cookie-backed `credentials: 'include'`.
  - Keep params serialization without token.

- Modify: `frontend-react/src/contexts/ConnectionContext.tsx`
  - Connect WS without query token.
  - Surface auth failure state.
  - If WS-A, ensure bootstrap happened before WS connect.

- Modify: `frontend-react/src/utils/config.ts`
  - Keep runtime config shape, but document token use.

- Possibly modify: `spa_server.py`
  - If WS-A, ensure session bootstrap/proxy supports cookie headers.
  - Tighten CSP `connect-src` from `ws://* wss://*` to explicit same-origin/local approved endpoints as part of Batch A.
  - Keep redaction.

### Service / operations

- Modify or deprecate: `jarvis-dashboard-backend.service`
  - Replace `--host 0.0.0.0` with `--host 127.0.0.1`, or mark file stale and not installable.

- Verify: `systemd/jarvis-dashboard.service`
  - Already uses `127.0.0.1` and `--no-access-log`.

- Create: `ops/logrotate/jarvis-dashboard-audit`
  - Candidate local project copy first; install to `/etc/logrotate.d/` only after explicit approval.

### Docs

- Update: `docs/security-hardening-batch-a/spec.md`
- Update: `docs/security-hardening-batch-a/plan.md`
- Update: `docs/security-hardening-batch-a/tasks.md`
- Update: `docs/security-hardening-batch-a/decisions.md`
- Update: `docs/TUTORIAL.md` after implementation.
- Update: Obsidian decision note and decision log.

## 5. API Routes

Potential new routes:

- `POST /api/plugins/jarvis-dashboard/v1/auth/session`
  - Input: no body required if Authorization header is present.
  - Output: `{ "status": "ok", "user": "..." }`
  - Side effect: sets `jarvis-dashboard-token` HttpOnly/SameSite cookie.

- `GET /api/plugins/jarvis-dashboard/v1/ready`
  - Output includes:
    - `status`: `ready` or `degraded`
    - `cache`: latest cache readable?
    - `kanban_db`: readable?
    - `audit_log`: writable/readable status without dumping contents
    - `version`

No public unauthenticated admin routes are added.

## 6. Data Model

No database schema changes planned.

Runtime auth/session data options:

- Preferred: reuse existing token as cookie value; no new persistence.
- Avoid: storing live tokens in files.
- Avoid: new SQLite table unless future multi-user session management is approved.

Audit rotation policy:

- Candidate retention: daily rotate, keep 14 days, compress old logs, create mode `0600 ubuntu ubuntu`.
- Do not truncate current log immediately during spec approval.

## 7. Edge Cases

- Browser cannot send `Authorization` header during native WebSocket handshake.
- CORS with credentials cannot use wildcard origins.
- Removing public IP origin may break direct public-IP access if the browser uses that exact origin; user must approve preferred access origin.
- Query-token fallback may remain in old bookmarks or generated URLs.
- SPA proxy must preserve cookies and auth headers correctly.
- If `TOKEN` is missing, UI should fail closed and clearly show auth failure.
- Service file drift can reappear if someone copies the stale root service file manually.
- `/ready` must not expose secrets, file contents, or full exception traces.

## 8. Testing Plan

Run after implementation:

1. Static/source checks

```bash
cd /home/ubuntu/.hermes/profiles/jarvis/plugins/jarvis-dashboard
python -m py_compile backend/server.py backend/core/websocket.py backend/auth/dependencies.py spa_server.py
npm --prefix frontend-react run build
```

2. Secret/token URL checks

```bash
cd /home/ubuntu/.hermes/profiles/jarvis/plugins/jarvis-dashboard
python3 - <<'PY'
from pathlib import Path
for p in [Path('frontend-react/src/api/client.ts'), Path('frontend-react/src/contexts/ConnectionContext.tsx')]:
    text = p.read_text()
    assert '?token=' not in text, p
print('no token query construction in React client')
PY
```

3. Backend smoke

```bash
curl -sS http://127.0.0.1:8502/api/plugins/jarvis-dashboard/health
curl -sS http://127.0.0.1:8502/api/plugins/jarvis-dashboard/ready
```

4. Auth smoke

```bash
TOKEN="$(grep '^JARVIS_DASHBOARD_DEV_TOKEN=' state/dashboard.env | cut -d= -f2-)"
curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1/dashboard/cache
```

5. CORS smoke

```bash
curl -i -X OPTIONS \
  -H 'Origin: http://127.0.0.1:8503' \
  -H 'Access-Control-Request-Method: GET' \
  http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1/dashboard/cache

curl -i -X OPTIONS \
  -H 'Origin: http://43.131.26.109:8503' \
  -H 'Access-Control-Request-Method: GET' \
  http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1/dashboard/cache
```

Expected: local origin allowed; public IP origin not credential-allowed unless Saiyudh explicitly approves it.

6. Listener smoke

```bash
ss -ltnp | grep -E '8502|8503'
```

Expected: both listeners on `127.0.0.1`, not `0.0.0.0`.

7. WebSocket smoke

Use a local Python/websockets or browser smoke script after selecting WS-A/WS-B. Expected:

- connect without `?token=` succeeds after approved auth bootstrap.
- unauthenticated WS fails closed.

8. Logrotate validation

```bash
logrotate --debug ops/logrotate/jarvis-dashboard-audit
```

If installing system-wide later:

```bash
sudo logrotate --debug /etc/logrotate.d/jarvis-dashboard-audit
```

## 9. Security Review Plan

Before release:

- Search for hardcoded secrets in changed files.
- Search for `?token=` in frontend runtime source.
- Verify logs redact query secrets.
- Verify no `allow_origins=["*"]` with credentials.
- Verify no public backend bind.
- Verify WS auth rejects unauthenticated clients.
- Verify `/ready` has no secret leakage.
- Boss/Security Lead final verdict required.

## 10. Rollback Plan

Rollback must be file-level and service-level:

1. Preserve backups before edits:
   - `backend/server.py`
   - `backend/core/websocket.py`
   - `backend/auth/dependencies.py`
   - `frontend-react/src/api/client.ts`
   - `frontend-react/src/contexts/ConnectionContext.tsx`
   - service files

2. If frontend build fails:
   - do not deploy new dist.
   - keep current SPA service running.

3. If backend smoke fails:
   - restore backed-up backend files.
   - restart backend service.
   - verify `/health` returns 200.

4. If auth migration locks out the UI:
   - restore previous frontend/backend files.
   - restart services.
   - document failure in `decisions.md` and Obsidian.

5. Never rollback by opening backend to `0.0.0.0`.
