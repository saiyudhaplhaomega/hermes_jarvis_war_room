# War Room Reference

Diataxis category: **reference** (autocomplete-style, not narrative).

## Modules

### Backend — `backend/server.py`
- L1-3: module docstring (project root, sys.path bootstrap).
- L10-19: FastAPI + middleware imports.
- L30-37: `plugin` APIRouter and CORS origins registry.
- L150-205: auth bootstrap, `/sse-session` (cookie-only SSE auth, 204), `/events` (denies `?token=`, requires cookie), `/ready` health.
- L1-3: SPA mount.
- L40-60: `create_app` factory wires routers.

### Auth — `backend/auth/dependencies.py`
- L1-20: token modes — `DEV_TOKEN`, `SESSION_COOKIE_NAME`, `QUERY_TOKEN_FALLBACK` flag.
- L30-60: `_bearer_token` and `_decode_subject`; query fallback default-deny.
- L67-78: `get_current_user_cookie_only` for SSE/EventSource.

### WebSocket — `backend/core/websocket.py`
- L1-40: WS auth via cookie only, denies query token.

### Route Policy — `backend/core/route_policy.py`
- L1-end: `EXPECTED_ROUTE_POLICY` tuple. Test in `tests/test_security_batch_a.py::test_route_policy_exact_allowlist_matches_registered_routes` enforces exact equality.

### Frontend Connection — `frontend-react/src/contexts/ConnectionContext.tsx`
- L17-45: SSE bootstrap — POST `/sse-session` then `new EventSource(url, { withCredentials: true })`. No `?token=`.

### SPA Server — `spa_server.py`
- L1-30: CSP and runtime-config guards (`_content_security_policy`, `RUNTIME_CONFIG`) must not embed `?token=`.

### Decision Brief Template — `decisions/brief-template.md`
- D-ID, Context, ELI10, Stakes, Recommendation, Options, Risks, Reversibility, Acceptance, split-if-5+.

### Decision Classifier — `decisions/classifier.md`
- Mechanical / Taste / User Challenge. User Challenge hard stop.

### Release Report Schema — `ops/release-report.schema.json`
- Required: phase, timestamp, commands (each with exit_code), gates (each with passed), artifacts (each with sha256).

### IRON LAW — `ops/iron_law.py`
- `FreshEvidenceGate.is_fresh(roots=[...])` returns True only when no source/config mtime exceeds the evidence timestamp.

### Docs Coverage — `ops/docs_coverage.py`
- `DiataxisGate(docs_root=...).missing_categories()` returns categories without a matching file in `docs/`.

### Release Validator — `ops/release.py`
- `ReleaseValidator(report=...).validate()` returns a list of error strings; empty list means release-ready.

## Routes (policy excerpt)
The full list lives in `backend/core/route_policy.py`. SSE surfaces:
- `POST /sse-session` — 204, sets HttpOnly cookie.
- `GET /events` — cookie-only SSE, 401 on `?token=`.
