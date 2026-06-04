# War Room Security Hardening Batch A — Tasks

```yaml
status: IMPLEMENTED_CONDITIONAL_PASS
coding_status: IMPLEMENTED_AND_TESTED
created: 2026-06-03T22:31:45+08:00
```

## Legend

- PLANNED: defined, not started.
- OPEN: ready after approval.
- DISCREPANCY: doc/code/runtime mismatch that must be resolved.
- BLOCKED: requires Saiyudh decision.
- CLOSED: verified complete.

## Phase 0 — Approval Gate

| ID | Task | File(s) | Status |
|---|---|---|---|
| SHA-000 | Saiyudh approves Batch A scope | `docs/security-hardening-batch-a/*` | CLOSED |
| SHA-001 | Select WebSocket auth design: WS-A cookie session is recommended; WS-B only if Saiyudh rejects cookie bootstrap | `plan.md` §3.3 | CLOSED |
| SHA-002 | Decide whether public IP origin must remain allowed | `backend/server.py` CORS | CLOSED |
| SHA-003 | Decide whether logrotate can be installed system-wide or project-only first | `ops/logrotate/*`, `/etc/logrotate.d/*` | CLOSED |
| SHA-004 | Decide query-token fallback policy: disabled by default vs temporary env-flag compatibility until Batch B or 2026-06-17 | auth helpers, docs | CLOSED |
| SHA-005 | Confirm WS session-expiry behavior: close auth/policy and require frontend re-bootstrap | WS auth/client | CLOSED |
| SHA-006 | Include CSP `connect-src` tightening in Batch A rather than deferring to Batch B | `spa_server.py` | CLOSED |

## Phase 1 — Auth Contract Tests First

| ID | Task | File(s) | Status |
|---|---|---|---|
| SHA-010 | Add/identify test harness for backend auth helpers | `backend/auth/dependencies.py`, tests TBD | CLOSED |
| SHA-011 | Write failing test: REST accepts `Authorization: Bearer` dev token | auth test | CLOSED |
| SHA-012 | Write failing test: REST still rejects missing/invalid auth | auth test | CLOSED |
| SHA-013 | Write failing test: WS auth path rejects unauthenticated connection | WS smoke/test | CLOSED |
| SHA-014 | Write failing test: normal React client source contains no `?token=` construction | source check script | CLOSED |
| SHA-015 | Write failing test: REST succeeds with `Authorization: Bearer` and no token URL | REST smoke/test | CLOSED |
| SHA-016 | Write failing test: WS-A cookie bootstrap sets cookie and WS connects without query token | WS smoke/test | CLOSED |
| SHA-017 | Write failing test: query-token fallback obeys explicit fallback flag or is rejected | auth/WS smoke/test | CLOSED |

## Phase 2 — Backend Auth + CORS + Readiness

| ID | Task | File(s) | Status |
|---|---|---|---|
| SHA-020 | Add bearer-token parsing to HTTP auth helper | `backend/auth/dependencies.py` | CLOSED |
| SHA-021 | Add selected WS auth helper | `backend/auth/dependencies.py`, `backend/core/websocket.py` | CLOSED |
| SHA-022 | If WS-A selected, add session bootstrap endpoint | `backend/api/auth.py`, `backend/server.py` | CLOSED |
| SHA-023 | Tighten CORS allowlist | `backend/server.py` | CLOSED |
| SHA-024 | Add direct-run `access_log=False` | `backend/server.py` | CLOSED |
| SHA-025 | Add `/ready` endpoint with no secret leakage | `backend/server.py` or new API module | CLOSED |
| SHA-026 | Run backend py_compile | backend files | CLOSED |
| SHA-027 | Tighten CSP `connect-src` from `ws://* wss://*` to approved local/same-origin endpoints | `spa_server.py` | CLOSED |

## Phase 3 — Frontend Auth Migration

| ID | Task | File(s) | Status |
|---|---|---|---|
| SHA-030 | Change URL builder to stop appending token query param | `frontend-react/src/api/client.ts` | CLOSED |
| SHA-031 | Add Authorization header or cookie credentials to REST fetches | `frontend-react/src/api/client.ts` | CLOSED |
| SHA-032 | Change WS connect path to omit query token | `frontend-react/src/contexts/ConnectionContext.tsx` | CLOSED |
| SHA-033 | Add visible auth failure state for WS connection | `frontend-react/src/contexts/ConnectionContext.tsx`, related UI if needed | CLOSED |
| SHA-034 | Build frontend | `frontend-react` | CLOSED |

## Phase 4 — Service Drift + Log Rotation

| ID | Task | File(s) | Status |
|---|---|---|---|
| SHA-040 | Fix or deprecate unsafe stale root backend service artifact | `jarvis-dashboard-backend.service` | CLOSED |
| SHA-041 | Verify installed service artifact remains `127.0.0.1` and `--no-access-log` | `systemd/jarvis-dashboard.service` | CLOSED |
| SHA-041a | Audit repo docs/scripts for references to stale root service artifact before changing it | project docs/scripts/service refs | CLOSED |
| SHA-042 | Create project-local logrotate candidate | `ops/logrotate/jarvis-dashboard-audit` | CLOSED |
| SHA-043 | Validate logrotate candidate with debug mode | `ops/logrotate/jarvis-dashboard-audit` | CLOSED |
| SHA-044 | Install logrotate system-wide only if separately approved | `/etc/logrotate.d/jarvis-dashboard-audit` | DEFERRED |

## Phase 5 — Runtime Smoke Tests

| ID | Task | Command | Status |
|---|---|---|---|
| SHA-050 | Restart backend only after code build passes | `systemctl restart ...` | CLOSED |
| SHA-051 | Verify listeners are localhost-only | `ss -ltnp | grep -E '8502|8503'` | CLOSED |
| SHA-052 | Verify liveness | `curl /health` | CLOSED |
| SHA-053 | Verify readiness | `curl /ready` | CLOSED |
| SHA-054 | Verify authenticated REST without token URL | `curl -H 'Authorization: Bearer ...'` | CLOSED |
| SHA-055 | Verify local CORS allowed | `curl -i -X OPTIONS -H Origin: http://127.0.0.1:8503 ...` | CLOSED |
| SHA-056 | Verify public IP CORS rejected by default | `curl -i -X OPTIONS -H Origin: http://43.131.26.109:8503 ...` | CLOSED |
| SHA-057 | Verify WS succeeds without query token through selected auth path | WS smoke script | CLOSED |
| SHA-058 | Verify WS unauthenticated fails closed | WS smoke script | CLOSED |
| SHA-059 | Verify frontend loads after build | browser/curl smoke | CLOSED |

## Phase 6 — Security Review + Tutorial + Memory

| ID | Task | File(s) | Status |
|---|---|---|---|
| SHA-060 | Run security scan over changed files | changed files | CLOSED |
| SHA-061 | Get Boss/Security Lead final verdict | review artifact | CLOSED |
| SHA-062 | Update tutorial explaining every changed file/function/snippet | `docs/TUTORIAL.md` | CLOSED |
| SHA-063 | Update Obsidian decision note and decision log | `~/Obsidian/Vault/08 Decisions/` | PLANNED |
| SHA-064 | Update Excalidraw only if architecture map changes | `~/Obsidian/Vault/05 Architecture/` | PLANNED |

## Open Decisions Before Coding

1. WS-A vs WS-B.
2. Public IP origin removal vs temporary allow.
3. Project-local logrotate candidate only vs system-wide install.
4. Whether query-token fallback remains temporarily for old bookmarks.

## Hard Blocks

- No code/config patching before Saiyudh approves this spec package.
- No k3s mutation.
- No public backend binding.
- No release without real smoke-test output.
