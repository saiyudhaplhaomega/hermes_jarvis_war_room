# Scout Synthesis — Architecture / Maintainability
# 2026-06-04 — MiniMax M3 (recommendation-only)

Status: DRAFT — for Saiyudh review.
Source scope: read-only inspection of uncommitted War Room work and prior scout archives.
No files were modified.

## 0. Bottom line

Batch A security work landed cleanly at the code level. The architecture is now
coherent around five small surfaces:

  1. backend/auth/dependencies.py  (bearer / cookie / opt-in query-fallback)
  2. backend/core/websocket.py     (pre-accept auth via the same helper)
  3. backend/server.py             (CORS, /auth/session, /ready, access_log=False)
  4. frontend-react auth + WS bootstrap in api/client.ts and ConnectionContext.tsx
  5. spa_server.py                 (CSP tightened, runtime config, log redaction)

The maintainability risks are now in the *adjacent* areas, not in Batch A itself:

  A. Uncommitted state, unversioned spec, and no tag for the Batch A release.
  B. Three independent "auth" surfaces that drift apart: dependencies.py, jwt_handler.py,
     and the new /auth/session cookie minting logic.
  C. /ready is a stub. Aggregator heartbeat and _scan_kanban() silent failures
     are still open (carryover from the live scout pass).
  D. The static service has two near-identical unit files in repo root
     and systemd/ with overlapping duties. Drift risk.
  E. docs/ now has 8 spec/decision/scout/timeline documents with overlapping
     scope. Easy to lose track of which is canonical.

What follows is ranked by ROI / risk.

---

## 1. Spec / version-control hygiene — HIGH ROI, LOW RISK

Observations:
  - Repo is at first commit (56f31b7) on main.
  - All Batch A changes (14 files, +318/-63) are uncommitted.
  - Root manifest.json still says "version": "1.1.0". TUTORIAL.md Batch A addendum
    calls itself v1.5.0, but no manifest, tag, or branch reflects that.
  - docs/security-hardening-batch-a/tasks.md shows SHA-044 (system-wide logrotate
    install) and SHA-063/SHA-064 (Obsidian / Excalidraw updates) as PLANNED/DEFERRED.
  - specs/decisions at root (spec.md, plan.md, tasks.md, decisions.md) are still
    Phase 2 v1.1.0; they do not reference Batch A.

Recommended updates (no code; docs/git only):
  - Add a CHANGELOG entry or update manifest.json to v1.5.0 only after
    Saiyudh signs off on the three carried caveats (HTTP-only cookie, token in
    injected HTML, public bind contract).
  - Commit Batch A as one squashed commit, or split into 4 logical commits:
        1. backend auth + CORS + /ready + access_log
        2. WebSocket pre-accept + /auth/session
        3. frontend auth migration + WS bootstrap
        4. services + logrotate candidate + tests + docs
    This keeps the audit trail readable and makes a future revert cheap.
  - Cross-link docs/spec.md and docs/security-hardening-batch-a/spec.md so
    the Batch A scope is discoverable from the top-level spec.
  - Add a one-line "scope: superset" header at the top of Batch A spec pointing
    back at the Phase 2 spec section it hardens.

Requires Saiyudh approval: bumping manifest version, commit policy.

Verify:
  - git log --oneline shows the expected commit(s) for Batch A.
  - git status is clean after commit.
  - manifest.json and TUTORIAL.md version strings agree.
  - docs/spec.md has a link to docs/security-hardening-batch-a/spec.md.

---

## 2. Auth helper consolidation — MEDIUM ROI, MEDIUM RISK

Observations:
  - backend/auth/dependencies.py is the only auth path after Batch A.
  - It still imports auth.jwt_handler.decode_token at call time (lazy import)
    inside _decode_subject(). That is fine but couples two modules.
  - The /auth/session endpoint in backend/server.py reads the dev token
    directly from os.environ, not via the auth helper. So the source of
    truth for "what is the current token?" lives in three places:
        - os.environ["JARVIS_DASHBOARD_DEV_TOKEN"]
        - spa_server.py RUNTIME_CONFIG (also reads env at module load)
        - /auth/session (reads env at request time)
  - spa_server.py computes RUNTIME_CONFIG at import time, so the token
    is baked into the first HTTP response. This is documented as a caveat
    but it also means rotating the token requires a static service restart.

Recommendations (require spec, not urgent):
  - Add a tiny auth/config facade in backend/auth/__init__.py that exposes:
        get_dev_token() -> str
        get_session_cookie_value() -> str
        build_session_cookie() -> dict (name, value, attrs)
    Have dependencies.py, server.py /auth/session, and (if applicable)
    spa_server.py consume it. This prevents silent drift.
  - Move spa_server.py's RUNTIME_CONFIG construction to a function so the
    token can be read per request. Cheaper fix: cache it but allow
    SIGHUP-style reload. Avoids the "restart to rotate token" footgun.
  - Document the current dev token / JWT token distinction in TUTORIAL.md.
    Today it says "Bearer ***" twice in different paragraphs without
    saying which token wins.

Requires Saiyudh approval: refactor scope; no behavior change.
Verify:
  - Existing tests/test_security_batch_a.py and tests/test_*_api.py still pass.
  - curl -H "Authorization: Bearer $T" /api/plugins/jarvis-dashboard/v1/ready
    still returns 200.
  - grep shows exactly one definition of SESSION_COOKIE_NAME and one of
    /auth/session.

---

## 3. /ready is a stub — MEDIUM ROI, MEDIUM RISK

Observations:
  - /ready currently returns:
        {"status": "ready", "plugin": "jarvis-dashboard", "version": "1.1.0"}
  - It does not actually probe:
        - aggregator last_success / last_error
        - kanban DB connectivity (read-only, short timeout)
        - disk usage on /home/ubuntu
        - journal disk-usage
  - Live scout 1 already flagged this as the highest operational risk after
    CORS / WS. Batch A answered the "endpoint exists" question but not the
    "endpoint actually tells the truth" question.

Recommendations (require spec, separate approval):
  - Expand /ready to a structured payload:
        {
          "status": "ready" | "degraded",
          "plugin": "jarvis-dashboard",
          "version": "1.5.0",
          "checks": {
            "aggregator":  {"ok": true,  "last_success_ts": ..., "last_error": null},
            "kanban":      {"ok": true,  "path": "...", "read_only": true},
            "audit_log":   {"ok": true,  "size_bytes": ..., "rotated": false},
            "jwt_secret":  {"ok": true,  "present": true, "mode": "600"}
          }
        }
  - Keep it authenticated so we never leak paths in unauth responses.
  - Have the SPA show a banner when /ready returns "degraded".

Requires Saiyudh approval: new spec for "readiness contract" (carryover from
SCOUT_FINDINGS_2026-06-03_LIVE_MINIMAX_M3.md).
Verify:
  - Smoke: temporarily break aggregator, /ready returns degraded.
  - Smoke: temporarily remove kanban DB read access, /ready returns degraded.
  - No secret values appear in /ready response body.

---

## 4. Aggregator heartbeat + _scan_kanban() silent exceptions — MEDIUM ROI, MEDIUM RISK

Observations:
  - backend/core/data_aggregator.py is not modified by Batch A, but the live
    scout 1 and the archived scout 1 both flagged it:
        - _scan_kanban() returns {} on any exception
        - no last_success / last_error exposure
        - no heartbeat back to the WS layer
  - backend/server.py's lifespan starts a background thread:
        t = threading.Thread(target=_aggregator_loop, daemon=True)
    that runs aggregator.run() in a loop. There is no health surface for it.
  - This is the most likely cause of "dashboard looks fine but data is stale"
    incidents. The new /ready endpoint should depend on it.

Recommendations (require spec, carryover from scout 1):
  - Add a small AggregatorState singleton:
        state.last_success_ts
        state.last_error
        state.last_run_duration_ms
  - Update _scan_kanban() to log the exception (rate-limited) and set
    state.last_error instead of returning {} silently.
  - Surface state via /ready (see section 3).

Requires Saiyudh approval: yes, this is exactly the item Boss ranked #3 in
the live scout. Tied to /ready so they ship together or not at all.
Verify:
  - Inject a fault into _scan_kanban (e.g. raise RuntimeError).
  - Confirm /ready reports degraded and state.last_error is populated.
  - Confirm WS /snapshot still serves a stale but valid payload (no crash).

---

## 5. Service-file drift — HIGH ROI, LOW RISK

Observations:
  - There are two backend service files in the repo:
        jarvis-dashboard-backend.service       (root, the legacy/older one)
        systemd/jarvis-dashboard.service      (the one linked to the live env)
    Both were 0.0.0.0-bound before Batch A. Batch A changed only the root
    one (jarvis-dashboard-backend.service: 0.0.0.0 -> 127.0.0.1).
    The systemd/jarvis-dashboard.service already had 127.0.0.1, so it
    stayed correct.
  - There are also two static service files:
        jarvis-dashboard-static.service       (root)
        systemd/jarvis-dashboard-static.service
    Both serve frontend-react/dist now and both bind 127.0.0.1. Good.
  - tests/test_security_batch_a.py:test_all_backend_service_artifacts_are_localhost_bound_and_disable_access_logs
    and test_all_static_service_artifacts_serve_react_dist_and_bind_localhost
    enforce this. Excellent guardrail.

Recommendations:
  - Decide canonical home: keep both pairs, or move the root ones to
    systemd/ and symlink / gitignore. Either is fine; what is not fine is
    silent re-divergence.
  - Add a one-line "this file is the canonical install target" comment
    at the top of systemd/jarvis-dashboard.service so future agents do
    not edit the wrong copy.
  - The two services use different EnvironmentFile handling (one uses
    EnvironmentFile=, the other has no env). Consolidate. Both should
    source state/dashboard.env.
  - Add an ops/install-services.sh that does:
        sudo install -m 0644 systemd/jarvis-dashboard.service        /etc/systemd/system/
        sudo install -m 0644 systemd/jarvis-dashboard-static.service /etc/systemd/system/
        sudo systemctl daemon-reload
    and is the only blessed path. Currently the install is by hand.

Requires Saiyudh approval: install path / consolidation choice.
Verify:
  - grep for "0.0.0.0" across all *.service files returns nothing.
  - Both pairs of service files have identical ExecStart host flags.
  - ops/install-services.sh is idempotent (running twice does not break).

---

## 6. Logrotate scope clarification — HIGH ROI, LOW RISK

Observations:
  - ops/logrotate/jarvis-dashboard-audit is a project-local candidate.
    Targets /home/ubuntu/.hermes/profiles/jarvis-dashboard/logs/audit.log
    (a path that does not currently exist in the live filesystem; the
    live audit log is /home/ubuntu/.hermes/state/audit/audit.jsonl per
    PROJECT_MEMORY.md and SCOUT_FINDINGS_2026-06-03_LIVE_MINIMAX_M3.md).
  - test_project_local_logrotate_candidate_exists_and_targets_audit_log
    asserts the path inside the file, not whether the file actually exists
    on disk. So a future agent who reads only tests will think the logrotate
    is wired up to the live audit log, but it is not.
  - Batch A decision DEC-006: install to /etc/logrotate.d/ only after
    explicit approval. SHA-044 is DEFERRED. Good. But the path mismatch
    must be resolved before any install.

Recommendations:
  - Either:
        (a) point logrotate at the real path
            /home/ubuntu/.hermes/state/audit/audit.jsonl
        (b) generate audit.log under the plugin's own logs/ dir and have
            backend/core/audit.py mirror to it.
  - Add a test that asserts the logrotate path actually resolves to a
    real file or to a directory that the backend creates at startup.
  - Document the chosen path in FEATURE_INVENTORY.md "Active Safety
    Invariants" and in PROJECT_MEMORY.md so the next agent does not
    have to grep.

Requires Saiyudh approval: which path the audit log uses, and whether
mirroring to logs/audit.log is acceptable.
Verify:
  - logrotate -d ops/logrotate/jarvis-dashboard-audit does not error
    about a missing parent directory.
  - After a system install, ls -la /var/lib/logrotate.status shows the
    rotation run.

---

## 7. Documentation sprawl — HIGH ROI, LOW RISK

Observations:
  - docs/ now contains:
        - spec.md, plan.md, tasks.md, decisions.md            (root, Phase 2 v1.1.0)
        - security-hardening-batch-a/{spec,plan,tasks,decisions}.md
        - FEATURE_INVENTORY.md  (canonical feature index)
        - PROJECT_MEMORY.md     (recovery timeline)
        - TUTORIAL.md           (now 327 lines + v1.5.0 addendum)
        - GOAL.md               (post-Batch-A goal, 39 lines)
        - SCOUT_FINDINGS_2026-06-03_MINIMAX_M3.md             (148 lines)
        - SCOUT_FINDINGS_2026-06-03_LIVE_MINIMAX_M3.md        (179 lines)
        - this synthesis file
  - COUNCIL_SYNTHESIS_v1.1.0.md and COUNCIL_SYNTHESIS_v1.1.0_PHASE2_DEPLOYMENT.md
    are still around from May 29 but are not referenced from current docs.
  - The two SCOUT_FINDINGS files are very similar; the LIVE one subsumes
    most of the other.

Recommendations:
  - Promote docs/decisions.md (root) to a true chronology; append a new
    "Batch A (2026-06-04)" section that references the per-batch
    decisions file. This is the single most valuable doc to maintain
    because Council will read it first.
  - In FEATURE_INVENTORY.md, add a new protected-items row for /auth/session
    cookie contract and /ready response shape. Currently only the WS
    endpoint is listed as [PROTECTED] for backend APIs.
  - TUTORIAL.md Batch A addendum is excellent but lives at the bottom; the
    auth section at the top still says "All endpoints require a token" with
    no mention of /auth/session. Move the addendum above the Security
    Model section, or duplicate the bearer-vs-cookie rule at the top.
  - Add docs/GOAL.md cross-link in PROJECT_MEMORY.md so the goal artefact
    is discoverable.
  - Consider merging SCOUT_FINDINGS_2026-06-03_MINIMAX_M3.md into the LIVE
    file as an "earlier pass" section. Reduces 148 LOC.

Requires Saiyudh approval: doc consolidation policy. No code change.
Verify:
  - grep -c "auth/session" docs/FEATURE_INVENTORY.md >= 1
  - grep -c "Batch A" docs/decisions.md >= 1
  - ls docs/SCOUT_FINDINGS_*.md | wc -l drops to 1 after merge.

---

## 8. Frontend React app hygiene — LOW ROI, MEDIUM RISK

Observations:
  - frontend-react/src/api/client.ts is clean: 115 lines, all calls funnel
    through authHeaders() and q(). No token-bearing URLs in the diff.
  - frontend-react/src/contexts/ConnectionContext.tsx is small (56 lines)
    but has no retry/backoff jitter and no explicit "auth_failed" state
    that the UI can render. The current onerror path just sets status to
    "closed"; a re-bootstrap race could open 2 WS in flight.
  - ConnectionProvider.connect() is async but called from useEffect with
    no cancellation. Strict-mode double-invoke in dev would open two WS.
  - CONFIG.TOKEN is the only thing the SPA needs from window.__CONFIG__.
    No rotation hook.

Recommendations:
  - Add an AbortController to ConnectionContext.connect so a second call
    cancels the in-flight /auth/session fetch.
  - Add a "ws_reconnect_attempts" counter that backs off (1s, 2s, 5s, 10s,
    30s) instead of fixed 3000ms.
  - Surface a distinct "auth_failed" status when /auth/session returns 401
    so the UI can show a clear message instead of a polling loop.
  - Consider extracting the WS + bootstrap to a small useWarRoomSocket()
    hook so other components (ArmyOperations, etc.) can subscribe to the
    same socket.

Requires Saiyudh approval: minor UX/refactor, low risk.
Verify:
  - Open dashboard, log in successfully, kill backend, observe status
    transitions: open -> closed -> polling with growing backoff.
  - In React StrictMode, only one /auth/session and one /ws connection
    are open at any moment.

---

## 9. Test coverage gaps — HIGH ROI, LOW RISK

Observations:
  - tests/test_security_batch_a.py has solid coverage for Batch A:
        - bearer auth + query-fallback gating
        - /auth/session cookie contract
        - CORS allow/deny
        - WS auth via cookie/bearer/query
        - CSP and runtime config content
        - source scan for ?token= in client.ts and ConnectionContext.tsx
        - logrotate candidate
        - both pairs of *.service files
  - tests/test_agent_growth_api.py, tests/test_army_api.py,
    tests/test_roles_api.py were updated to set
    JARVIS_DASHBOARD_QUERY_TOKEN_FALLBACK=1, presumably because they
    still construct ?token= URLs internally. That is a code smell:
    production paths should not need a fallback flag to pass tests.
  - No coverage for: CSP regression (e.g. someone re-adds ws://*),
    audit log rotation actually happening, JWT cookie expiry handling,
    WS close code on session expiry.
  - No frontend tests. There is no Jest/Vitest config in frontend-react/
    that I can see. The source scan in test_frontend_source_does_not_construct_token_query_urls
    is a static check, not a runtime test.

Recommendations:
  - Migrate the test_agent_growth_api.py / test_army_api.py / test_roles_api.py
    suites to use Authorization headers, then remove the
    JARVIS_DASHBOARD_QUERY_TOKEN_FALLBACK=1 hack. Better: use the /auth/session
    helper to set a cookie and pass that.
  - Add a CSRF concern test: an attacker page on the same host cannot
    make a POST /army/runs without the auth cookie. (Same-origin so this
    is partly by design, but worth a regression test.)
  - Add a /ready degraded-path test once /ready is implemented.
  - Add a Jest/Vitest setup for frontend-react with at least:
        - api/client.ts authHeaders shape
        - ConnectionContext WS bootstrap ordering
  - Add a test that asserts spa_server.py RUNTIME_CONFIG no longer
    contains a literal `token=` query.

Requires Saiyudh approval: testing strategy; small refactors.
Verify:
  - ./venv/bin/python -m pytest tests -q still passes after removing
    the QUERY_TOKEN_FALLBACK=1 hack from the three legacy tests.
  - npm --prefix frontend-react test runs a single smoke test.

---

## 10. Excalidraw / Obsidian memory — MEDIUM ROI, LOW RISK

Observations:
  - docs/architecture-v1.1.0.excalidraw is the canonical map.
  - docs/army-operations-v1.4.0.excalidraw is in place.
  - PROJECT_MEMORY.md links to SCOUT_FINDINGS files but not to a
    War Room auth-flow map.
  - Batch A changes (cookie bootstrap, /ready, new CORS, /auth/session)
    are not represented in the architecture map.
  - Obsidian updates are PLANNED (SHA-063, SHA-064). No Obsidian file
    was found in this scout pass (outside the project scope).

Recommendations:
  - Add a single v1.5.0 auth-flow diagram to
    docs/auth-flow-v1.5.0.excalidraw. The current data flow is:
        React -> /auth/session (bearer) -> Set-Cookie -> /ws (cookie)
    Worth one drawing.
  - Update docs/architecture-v1.1.0.excalidraw to mark the new
    /ready and /auth/session boxes in a different color, with a
    legend note "added in v1.5.0 Batch A".
  - After Boss/Manager approve this synthesis, create the Obsidian
    decision note under ~/Obsidian/Vault/08 Decisions/ as planned.

Requires Saiyudh approval: visual scope, not code.
Verify:
  - The new auth-flow map opens in Excalidraw and references all four
    surfaces (bearer header, cookie, /auth/session, /ws).
  - The v1.1.0 architecture map is not deleted; it is annotated.

---

## 11. What does NOT need changing

For completeness, here is what Batch A got right and should not be
re-engineered:

  - The lazy import of auth.jwt_handler.decode_token in _decode_subject.
  - The use of starlette.middleware.base.BaseHTTPMiddleware for
    RateLimitMiddleware. Could be ASGI but works.
  - CORS being a literal list in server.py. A env-driven list would be
    marginally nicer but adds a config surface for a 4-line benefit.
  - The system prompt rule that backend uvicorn access logs stay off.
  - The /ready endpoint requiring auth (so it does not leak paths).
  - The CSP tightening: explicit ws://127.0.0.1:8503 / wss://... entries
    instead of ws://* is a real improvement, not just cosmetic.
  - The PR-style single file change to jarvis-dashboard-backend.service
    (0.0.0.0 -> 127.0.0.1) is the kind of one-line security win that
    compounds.

---

## 12. Ranked recommendation list (final)

By ROI / risk:

  1. Commit Batch A as 4 logical commits and bump manifest to v1.5.0.
     (LOW risk, immediate audit win, blocks all later doc work.)
  2. Wire the project-local logrotate to the real audit log path and
     write a regression test that resolves the path. (LOW risk, fixes
     a latent gap before any /etc install.)
  3. Promote docs/decisions.md to a true chronology with a "Batch A"
     section. (LOW risk, doc-only, helps Council reads.)
  4. Decide canonical service-file home and add ops/install-services.sh.
     (LOW risk, prevents re-divergence.)
  5. Add a small auth facade so the dev token source-of-truth lives in
     one module. (MED risk if rushed, MED ROI.)
  6. Replace JARVIS_DASHBOARD_QUERY_TOKEN_FALLBACK=1 hack in the three
     legacy test suites with bearer/cookie auth. (LOW risk, removes
     a future footgun.)
  7. Implement real /ready with aggregator + kanban + audit + jwt checks.
     (MED risk, HIGH ROI, but tied to spec approval.)
  8. Implement AggregatorState + non-silent _scan_kanban error path.
     (MED risk, HIGH ROI, tied to /ready.)
  9. Add AbortController + exponential backoff to ConnectionContext.
     (LOW risk, LOW ROI, but small.)
 10. Add frontend-react unit test scaffold. (LOW risk, MED ROI,
     but does not block release.)
 11. Add auth-flow Excalidraw + v1.5.0 annotations to architecture map.
     (LOW risk, MED ROI for future Council reads.)
 12. Merge the two SCOUT_FINDINGS files. (LOW risk, doc-only.)

Items 7 and 8 are the most strategically important but they are
already on the deferred list per the live scout and need their own
spec. Recommend they go into a "Batch B / readiness contract" spec
drafted next, not folded into Batch A.

---

## 13. Approval gates summary

Items that require fresh Saiyudh approval before any code or runtime
change:

  - manifest version bump and commit policy (section 1)
  - auth facade refactor (section 2)
  - /ready expansion spec (section 3)
  - aggregator heartbeat spec (section 4)
  - canonical service-file home and install path (section 5)
  - audit log path reconciliation (section 6)
  - ConnectionContext refactor (section 8)
  - frontend test scaffold (section 9)
  - Excalidraw updates (section 10)

Items that are docs/git only and could be done by a single approved
agent without further gates:

  - commit policy and changelog (section 1)
  - doc consolidation and decisions.md chronology (section 7)
  - SCOUT_FINDINGS merge (section 12)
  - /auth/session + /ready rows in FEATURE_INVENTORY.md (section 7)

No items in this scout require changes to:
  - k3s, Zeabur, ingress, DNS
  - public-bind of any War Room port
  - the dev token value
  - the dashboard .env file or state/dashboard.env
  - any other Hermes profile, agent, or skill

---

## 14. Verification commands (for the human or for a follow-up scout)

  cd /home/ubuntu/.hermes/profiles/jarvis/plugins/jarvis-dashboard
  git status --short
  git log --oneline -5
  grep -rn "0.0.0.0" --include="*.service" .
  grep -rn "ws://\*" spa_server.py frontend-react/src
  grep -rn "query_params.get(.token.)" backend/  # should be empty in normal paths
  ./venv/bin/python -m pytest tests -q
  logrotate -d ops/logrotate/jarvis-dashboard-audit
  curl -s -H "Authorization: Bearer $JARVIS_DASHBOARD_DEV_TOKEN" \
      http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1/ready
