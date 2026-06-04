# War Room Security Hardening Batch A — Product Spec

```yaml
name: war-room-security-hardening-batch-a
project: jarvis-war-room-dashboard
version: 0.1.0
status: DRAFT_FOR_SAIYUDH_APPROVAL
created: 2026-06-03T22:31:45+08:00
owner: jarvis-security-lead
boss_review: JARVIS-2026-0603-SECURITY-HARDENING-DISCUSSION
coding_status: NOT_APPROVED
```

## 1. Founder Grill Summary

Saiyudh asked to harden the War Room after VPS disk/RAM and MiniMax scout findings. Boss reviewed first and ruled:

- k3s is Zeabur platform infrastructure and must stay read-only.
- War Room runs outside k3s on systemd/local listeners.
- Security hardening is worthwhile, but no code/config changes before a written scope and Saiyudh approval.
- Batch A should target exposure/auth/logging risks, not unrelated roadmap UI.

This spec is the approval packet. It does not implement anything.

## 2. Problem Statement

The War Room currently works, but it carries several avoidable security and operations risks:

1. WebSocket auth relies on a query-token design in the backend and/or frontend runtime path.
2. REST API calls put `token` in query strings from the React client.
3. Credentialed CORS allows the public IP origin `http://43.131.26.109:8503`.
4. One backend service artifact binds `0.0.0.0:8502`, while the live installed service binds `127.0.0.1:8502`.
5. The backend direct-run path does not explicitly disable access logs.
6. Audit logs have no local rotation policy.
7. `/health` is liveness only, with no readiness contract.

None of these require touching k3s.

## 3. Goals

G1. Remove token-bearing URLs from normal frontend API and WebSocket traffic.

G2. Keep backend and frontend bound to localhost unless Saiyudh separately approves public exposure.

G3. Keep credentialed CORS restricted to explicit local/Tailnet/domain origins; no broad wildcard and no accidental public-IP credential origin by default.

G4. Ensure all backend startup paths keep access logs disabled or redacted so token values do not leak if legacy query tokens still appear.

G5. Add audit log rotation/retention so the VPS does not silently fill disk.

G6. Add a readiness endpoint that reports whether required local dependencies are actually usable.

G7. Preserve existing War Room UI contracts and runtime boundaries.

## 4. Non-Goals

N1. Do not modify k3s, kubectl resources, Zeabur pods, Zeabur DNS, or Zeabur ingress.

N2. Do not replace the authentication system with full OAuth/OIDC in this batch.

N3. Do not expose the backend publicly.

N4. Do not redesign the War Room UI.

N5. Do not implement on-demand Discord agent startup in this batch. That requires a separate architecture spec and Obsidian decision.

N6. Do not rotate secrets automatically unless Saiyudh explicitly approves a token rotation window.

## 5. Current Evidence

Live/runtime evidence gathered on 2026-06-03:

- Live backend listener: `127.0.0.1:8502`.
- Live SPA listener: `127.0.0.1:8503`.
- Installed backend service file at `systemd/jarvis-dashboard.service` uses:
  - `--host 127.0.0.1`
  - `--no-access-log`
- Stale/root backend service artifact at `jarvis-dashboard-backend.service` uses:
  - `--host 0.0.0.0`
  - `--no-access-log`
- `backend/server.py` CORS currently includes:
  - `http://127.0.0.1:8503`
  - `http://127.0.0.1:8513`
  - `http://43.131.26.109:8503`
  - `http://localhost:8503`
  - `http://localhost:8513`
- `backend/server.py` direct run currently calls:
  - `uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")`
- `backend/core/websocket.py` authenticates using:
  - `websocket.query_params.get("token", "")`
- `frontend-react/src/api/client.ts` builds URLs as:
  - `${API}${path}?token=${TOKEN}`
- `spa_server.py` injects `window.__CONFIG__` with `TOKEN` and `WS_URL`.
- `spa_server.py` already redacts token-like query params in static-server logs.

## 6. User-Facing Behavior

After Batch A is implemented and approved:

- The dashboard should still open at the same War Room URL.
- Normal API requests should authenticate without putting the token in the URL.
- WebSocket connection should authenticate without `?token=` in the URL.
- If auth fails, the UI should show closed/polling/auth-failed state rather than silently looping forever.
- Backend should remain localhost-bound.
- `/health` remains simple liveness.
- New `/ready` endpoint reports readiness details.
- Audit log retention becomes bounded.

## 7. Security Requirements

S1. No new hardcoded secret values in repo files.

S2. The frontend may receive runtime config from `spa_server.py`, but generated files committed to the repo must not contain live token values.

S3. REST API auth should use `Authorization: Bearer ***` from the React client through the SPA proxy. The backend must parse bearer auth before considering any legacy query token.

S4. WebSocket auth should use the WS-A cookie/session bootstrap unless Saiyudh chooses another option:
- Browser calls `POST /api/plugins/jarvis-dashboard/v1/auth/session` with `Authorization: Bearer ***`.
- Backend validates and sets `jarvis-dashboard-token` as `HttpOnly; SameSite=Lax; Path=/api/plugins/jarvis-dashboard; Max-Age=3600`.
- Browser opens WS with no query token.
- Backend verifies the cookie before useful session behavior.

S4a. WS-A is valid only for the current same-origin/same-site SPA proxy topology. If War Room is served cross-origin over plain HTTP, stop and redesign auth before implementation.

S4b. Any query-token fallback must be disabled by default or controlled by an explicit env flag with deprecation notes, redaction, and a removal deadline. If kept, the fallback expires no later than Batch B security hardening or 2026-06-17, whichever comes first.

S4c. Active WebSocket connections must enforce auth expiry. On session expiry or auth invalidation, the server closes the connection with a documented auth/policy code and the frontend must re-bootstrap auth before reconnecting.

S5. CORS with `allow_credentials=True` must never use `allow_origins=["*"]`.

S6. Public IP credentialed CORS origin must be removed by default unless Saiyudh approves it as an explicit remote-access origin.

S7. All logs that can include URLs must redact `token`, `api_key`, `key`, and `password` query values.

S8. Audit log rotation must be local-only and must not delete current logs immediately during install.

## 8. Technical Constraints

C1. Preserve War Room project-local boundary under:
`/home/ubuntu/.hermes/profiles/jarvis/plugins/jarvis-dashboard/`

C2. Preserve Hermes runtime Kanban separation:
- War Room/user/company Kanban: `/home/ubuntu/.hermes/kanban.db`
- Hermes runtime dispatcher Kanban: `/home/ubuntu/.hermes/hermes-kanban.db`

C3. Do not mutate `/home/ubuntu/.hermes/kanban.db` to satisfy runtime dispatcher schema drift.

C4. Do not touch k3s.

C5. No dependency installation without separate approval.

C6. No release without smoke tests, security review, tutorial/docs, and Obsidian update.

## 9. Acceptance Criteria

A1. API token no longer appears in normal React fetch URLs.

A2. WebSocket URL no longer contains `?token=` in normal operation.

A3. Backend accepts the new auth path for REST and WS.

A4. Existing query-token auth remains only as a temporary compatibility fallback if required, with deprecation note and redaction.

A5. CORS no longer includes `http://43.131.26.109:8503` by default.

A6. Both backend service artifacts bind `127.0.0.1`, or stale unsafe artifact is clearly deprecated/renamed.

A7. Backend direct `uvicorn.run()` disables access logs.

A8. `/api/plugins/jarvis-dashboard/v1/ready` returns structured readiness.

A9. Log rotation policy exists and validates syntactically.

A10. Smoke tests prove backend health, readiness, authenticated REST, WS auth, CORS rejection/allowance, localhost binding, and no token in new client URLs.

## 10. Release Gate

Batch A is not released until all are true:

- [ ] Saiyudh approves this spec scope.
- [ ] `plan.md` is complete.
- [ ] `tasks.md` is complete.
- [ ] `decisions.md` is complete.
- [ ] Implementation is complete.
- [ ] Build passes.
- [ ] Smoke tests pass with real output.
- [ ] Security review passes.
- [ ] Tutorial/docs explain every changed file/function/snippet.
- [ ] Obsidian decision note and decision log are updated.
- [ ] No k3s mutation occurred.
