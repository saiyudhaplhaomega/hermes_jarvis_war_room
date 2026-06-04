# War Room Security Hardening Batch A — Decisions

```yaml
status: IMPLEMENTED_CONDITIONAL_PASS
created: 2026-06-03T22:31:45+08:00
coding_status: IMPLEMENTED_AND_TESTED
```

## DEC-001 — k3s is read-only Zeabur infrastructure

Status: CLOSED

Decision: Do not modify k3s, kubectl resources, Zeabur pods, Zeabur ingresses, Zeabur DNS, or k3s service configuration as part of War Room security hardening.

Evidence:
- k3s pods are Zeabur/platform services: `zeabur-kube-watch`, `zeabur-dns`, `zeabur-log-api`, `cadvisor`, `fluent-bit`, `vector-aggregator`, `ingress-controller`, `nats`, `node-exporter`.
- Ingress hosts use `*.servers.onzeabur.com`.
- War Room backend and SPA are local systemd/listener processes outside k3s.

Rationale: k3s is not the War Room app runtime. Mutating it could break managed hosting and observability.

## DEC-002 — Batch A is scoped to War Room exposure/auth/logging hardening

Status: CLOSED

Decision: Batch A includes WebSocket auth migration, REST token URL removal, CORS tightening, backend bind drift correction, direct-run access-log hardening, audit log rotation, and readiness endpoint.

Rationale: These are high-value security/ops improvements directly tied to the MiniMax scout findings and live evidence.

## DEC-003 — On-demand Discord agent startup is separate architecture work

Status: DEFERRED_TO_SEPARATE_SPEC

Decision: Do not implement summon-on-demand Discord agents in this security batch.

Rationale: Boss approved the direction, but it changes agent lifecycle architecture and needs a separate supervisor design, Obsidian decision, timeout model, and approval gates.

## DEC-004 — Preferred WebSocket auth direction is cookie/session bootstrap

Status: CLOSED

Decision: Prefer WS-A: frontend calls a session bootstrap endpoint with bearer auth, backend sets an HttpOnly/SameSite cookie scoped to `/api/plugins/jarvis-dashboard`, and native browser WebSocket connects without query token.

Specific proposed cookie contract:
- Cookie name: `jarvis-dashboard-token`
- Attributes: `HttpOnly; SameSite=Lax; Path=/api/plugins/jarvis-dashboard; Max-Age=3600`
- Normal topology: same-origin/same-site through `spa_server.py` proxy.
- No persistent server-side session store in Batch A.

Rationale: Browsers cannot set arbitrary Authorization headers during native WebSocket handshake. Cookie/session bootstrap avoids token-in-query and avoids accepting unauthenticated WebSocket sessions as normal.

Constraints: If War Room is served cross-origin over plain HTTP, stop and redesign. Do not silently weaken to `SameSite=None` without HTTPS/security review.

Alternatives:
- WS-B first-message auth: easier but less clean because the socket is accepted before authentication.
- WS-C query token: rejected as final outcome because it preserves the finding.

## DEC-005 — Public IP credentialed CORS should be removed by default

Status: CLOSED

Decision: Remove `http://43.131.26.109:8503` from default credentialed CORS origins unless Saiyudh explicitly wants direct public-IP browser access.

Rationale: Credentialed CORS should be narrow and intentional. Public IP origins are brittle and widen exposure surface.

## DEC-006 — Logrotate starts project-local, system install needs explicit approval

Status: CLOSED

Decision: Create a project-local logrotate candidate first; install to `/etc/logrotate.d/` only after explicit approval.

Rationale: `/etc` changes are system-wide side effects and should not happen during draft planning.

## DEC-007 — Query-token fallback may remain temporarily only if explicitly documented

Status: CLOSED

Decision: Keep query-token auth only as a temporary compatibility fallback if necessary; do not use it for normal frontend paths. If kept, fallback must be behind an explicit env flag and must be removed no later than Batch B security hardening or 2026-06-17, whichever comes first.

Rationale: Removing every fallback at once may lock out old bookmarks/scripts. But leaving it as the normal path defeats the hardening goal.

## DEC-008 — No release without smoke tests and security review

Status: CLOSED

Decision: Batch A cannot be released without build, smoke tests, security review, tutorial/docs, and Obsidian update.

Rationale: Company OS release gates apply.


## DEC-009 — Boss/Security conditional pass caveats

Status: CLOSED

Decision: Batch A carries three documented caveats: localhost HTTP cookies use `secure=False`; the SPA runtime token is present in page HTML as `window.__CONFIG__.TOKEN`; root and systemd service artifacts must stay aligned on `frontend-react/dist` and localhost binding.

Evidence:
- Boss/Security review returned CONDITIONAL PASS with no live-restart blockers.
- Tutorial documents all three caveats.
- Tests cover backend and static service artifacts.

Rationale: These caveats are acceptable for the current single-user localhost War Room, but must trigger new security review before public/shared/TLS topology changes.
