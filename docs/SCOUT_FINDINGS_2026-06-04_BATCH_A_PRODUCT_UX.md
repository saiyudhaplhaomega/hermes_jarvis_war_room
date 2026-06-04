# Scout Findings — 2026-06-04 — Batch A Product/UX Update Scout

```yaml
scout: MiniMax-M3 (recommendation-only)
scope: War Room product/UX updates enabled by Batch A security release
project: jarvis-war-room-dashboard
read_only: true
status: SCOUT_RECOMMENDATIONS_PENDING_SAIYUDH_APPROVAL
sources:
  - docs/security-hardening-batch-a/{spec,plan,decisions,tasks}.md
  - docs/PROJECT_MEMORY.md
  - docs/FEATURE_INVENTORY.md
  - frontend-react/src/api/client.ts
  - frontend-react/src/contexts/ConnectionContext.tsx
```

## Reading notes (what Batch A actually unlocks for UX)

1. Token is no longer in REST URLs (SHA-030) and WS connects without `?token=` (SHA-032) — connection telemetry can now be shared in screenshots/incident notes without redacting.
2. Backend exposes `/ready` (SHA-025) — War Room can finally tell the user "auth service unreachable" vs "kanban store locked" instead of one generic "polling" dot.
3. CORS no longer leaks the public IP origin (SHA-023, DEC-005) — War Room can be demoed/screenshot on localhost + tunnel without the security footer saying "public IP allowed".
4. Audit log has bounded retention policy (SHA-042) — long-term "Session Review" and "Audit Replay" features become viable without the user worrying about disk fill.
5. Three Caveats from DEC-009 still apply (HTTP `secure=False`, token in `window.__CONFIG__.TOKEN`, service-artifact alignment). Any recommendation that involves external sharing must flag caveat 1 and 2 explicitly.

## Scouting principle

All recommendations are scout inputs. None are auto-approved. Each item: rationale → spec-need → smoke/acceptance idea → usefulness × risk. Usefulness = how much the item moves War Room toward a "dramatic, full-page, adaptive conversational experience" the user explicitly asked for. Risk = how much it touches Batch A caveats, protected DOM/JS contracts, or k3s-adjacent surfaces.

---

## Tier 1 — Highest usefulness, lowest risk (do these first)

### R1. Connection story: replace the single dot with a 4-state adaptive banner

Usefulness: 5/5. Risk: 1/5.

**Why now.** The `conn-dot`/`conn-text` indicator (FEATURE_INVENTORY L64) was originally wired to `polling/open/closed`. Batch A adds `/ready` + structured readiness. The dot is now under-using the data the backend already returns. A first-class, full-page, dramatic connection banner that names the actual cause ("auth expired — re-bootstrap", "kanban store locked", "backend not ready", "websocket open") turns a confusing status into a guided response.

**Spec need.** New mini-spec `docs/connection-experience-batch-b.md`:
- Map `ConnectionContext.status` + `/ready` body to user-visible state machine.
- 4 states: `open`, `bootstrap`, `reauth-needed`, `backend-not-ready` (rename internal enum or add derived state).
- Add visible "Re-authenticate" affordance for `reauth-needed` (calls `POST /auth/session` again, shows countdown to Max-Age expiry).
- Detect intent shift: if user types while `reauth-needed`, prompt "Auth expired — re-bootstrap and send?" instead of silently swallowing input. This is the literal "intent shift detection" requirement.

**Acceptance / smoke.** Playwright (or curl+headless smoke) that:
1. Boots dashboard with valid token → state `open` within 2s.
2. Invalidates session cookie → state transitions to `reauth-needed` within 10s, banner shows.
3. User types in `nl-input` while `reauth-needed` → input is buffered, prompt appears, no silent drop.
4. `/ready` reports `kanban=unavailable` → banner shows `backend-not-ready` and a "What does this mean?" expandable.
5. Existing `chat-thread` DOM id and `sendChat` JS contract untouched.

---

### R2. Frustration / "aaaaaa" detection in dispatch terminal

Usefulness: 5/5. Risk: 1/5.

**Why now.** The user explicitly demanded "detect intent shifts / frustration / answer-progression". The dispatch terminal is the only place this matters operationally. Current `sendChat` (FEATURE_INVENTORY L56) is fire-and-forget.

**Spec need.** Append to `connection-experience-batch-b.md` or new `docs/conversational-handler-ux.md`:
- Local, no-LLM heuristic on `nl-input` input: repeated chars / all-lowercase rants / "no idea" / "isn't working" → switch response mode from "answer" to "diagnose".
- "Diagnose" mode prepends a structured "what I checked" preamble to the model call and surfaces 3 quick actions: "Run health check", "Open session drawer", "Open audit strip". This is the "answer-progression" signal.
- "Not working" trigger: if user has sent 2+ messages in 60s with low model confidence / non-2xx, automatically surface `/health` + `/ready` status inline in the thread.
- No PII or chat content sent to a new backend; this is pure client-side state.

**Acceptance / smoke.**
1. Type `aaaaaa` → mode badge in `chat-thread` flips to `diagnose`.
2. Type `this isn't working` twice within 60s → inline status panel from `/health` and `/ready` appears in-thread.
3. Type a clean question → mode stays `answer`, no false positive.
4. `chat-thread` DOM contract preserved; only new sibling elements with `chat-*` namespace added.

---

### R3. Audit Replay view (read-only) as a project-tab

Usefulness: 4/5. Risk: 1/5.

**Why now.** Audit rotation policy now bounded (SHA-042) — the disk-fill worry that blocked any "browse history" feature is gone. The protected `audit-strip` (FEATURE_INVENTORY L58) is a fixed bottom timeline; a full-page Replay view that filters by project, agent, decision type is a natural extension and feeds the "answer-progression" loop (user can see "this is what happened last time you hit this").

**Spec need.** New `docs/audit-replay-view.md`:
- New route/section in SPA (not a popup): `war-room/audit`.
- Filters: project (default = active), agent, event type, time range.
- Reuses existing `GET /audit*` endpoints; no new backend unless pagination missing.
- Each row is expandable to show full audit event JSON; never raw tokens (already redacted per S7).

**Acceptance / smoke.**
1. Open `/war-room/audit` → 200, lists events scoped to active project by default.
2. Filter by `agent=jarvis-security-lead` → list narrows; no other agent's rows leak.
3. Click a row → JSON expands; verify `token`/`api_key` fields either absent or redacted.
4. `/health` and `/ready` still 200 after navigation.

---

## Tier 2 — High usefulness, moderate risk

### R4. Per-project "Security Posture" panel (Batch A audit trail for the user)

Usefulness: 4/5. Risk: 2/5.

**Why now.** Batch A shipped but the user (Saiyudh) and any future War Room collaborator has no in-UI proof. A "Security Posture" panel under the active-project tab showing: backend bind (127.0.0.1 ✓), CORS allowlist count, audit log size, last rotation date, readiness score, conditional-pass caveats from DEC-009 — turns the abstract "we hardened" into a visible artifact. Highly dramatic, full-page, project-scoped.

**Spec need.** `docs/security-posture-panel.md`:
- New backend endpoint `GET /api/plugins/jarvis-dashboard/v1/security/posture` that aggregates: backend bind, CORS origin count, audit log bytes, last rotation, `/ready` body, `window.__CONFIG__.TOKEN` presence flag.
- New SPA panel under project tab. Renders all 3 DEC-009 caveats as a top-of-panel warning card (they are *current* truth, not bugs).
- Never displays the actual token value or cookie value.

**Acceptance / smoke.**
1. `GET /security/posture` returns JSON with no token leakage (grep response for `TOKEN` literal must be 0).
2. Panel renders in < 500ms; cave ats visible at top.
3. If backend is rebound to `0.0.0.0` (regression), panel shows red bind-warning — proves it's a real monitor, not a sticker.

---

### R5. Council Chamber: surface Boss verdict and Manager objections in a full page

Usefulness: 4/5. Risk: 2/5.

**Why now.** `council-panel` is `[PROTECTED]` (FEATURE_INVENTORY L60) but currently a placeholder. Batch A's decisions.md is the perfect content seed — Boss ruled first, Manager `NO_OBJECTIONS`, three caveats. A War Room that dramatizes the council's own verdict on a just-shipped batch is the most on-brand "full-page, dramatic" thing possible and directly serves the "use the council in every step" standing order by showing the council's work after the fact.

**Spec need.** `docs/council-chamber-live.md`:
- Read `docs/security-hardening-batch-a/decisions.md` and surface each `DEC-NNN` with status badge.
- Add live vote indicator (Boss/Manager/Secretary) for current active work item, sourced from a small `/council/active` endpoint (or stub if absent).
- Add "challenge this decision" affordance → creates a Kanban card under active project tagged `council-challenge`.

**Acceptance / smoke.**
1. Visit `/war-room/council` → 200, lists DEC-001..DEC-009 with correct CLOSED/DEFERRED/PLANNED status.
2. Click "challenge" → modal asks for reason → POST creates a project-scoped Kanban card; verify it appears under the active project.
3. No protected DOM id renamed.

---

## Tier 3 — Useful, higher risk (defer until R1-R4 ship)

### R6. Per-session "Re-bootstrap now" inline action

Usefulness: 3/5. Risk: 3/5.

The session drawer (FEATURE_INVENTORY L57) currently lists past sessions. Batch A's `Max-Age=3600` cookie (DEC-004) means a user can land in `reauth-needed` mid-session. A "Re-bootstrap and replay" button on each session row would close the loop with R1. Risk: requires mutating session state and confirming the user wants to re-execute a 1-hour-old prompt. Defer until R1 ships and we know the actual expiry UX.

### R7. Intent-shift → auto-route to scout mode

Usefulness: 3/5. Risk: 3/5.

When the user types "is this safe?" or "audit this", route to a scout-style mode (read-only, no edits) instead of the default action mode. Ties into R2 frustration detection. Risk: model routing decisions in the dispatch terminal are a larger surface than heuristics; needs a separate spec and Boss review per cost-aware-router skill.

### R8. Full-page dramatic P0-P8 roadmap (Boss-blocked per archive)

Usefulness: 4/5. Risk: 4/5.

`PROJECT_MEMORY.md` line 107 explicitly lists "P0-P8 roadmap taxonomy before any roadmap/ticker UI" as a Boss-blocked follow-up. A roadmap ticker is highly dramatic and obviously valuable, but the spec is not yet approved. Scout should *not* recommend UI work here; recommend the taxonomy spec as the precursor. Filing for the record, not the backlog.

---

## Cross-cutting acceptance gates (apply to all Tier 1+2)

- No mutation to `/home/ubuntu/.hermes/kanban.db` (C2/C3).
- No k3s mutation (C4).
- `chat-thread`, `nl-input`, `mode-select`, `project-select`, `workspace-list` DOM contracts untouched.
- `chat-history` / `cmd-input` / `cmd-send` must not reappear (PROJECT_MEMORY L42).
- New SPA sections live under existing top-level nav, not as a popup modal — user explicitly wants full-page.
- All new copy follows dramatic War Room tone (cost/timeline/agent-rollcall headers) but does not leak Batch A caveat #1 ("HTTP cookies are not `secure`") into marketing language — the user must still see it.
- All items gated by Boss/Security Lead review of an explicit mini-spec before code; spec-first, no prototype.

## Recommended approval packet ordering (scout's view)

1. Approve R1 + R2 as a single combined spec `connection-and-conversational-ux.md` — both touch `nl-input`/`chat-thread`, designing them together avoids two refactors.
2. Approve R3 (audit replay) — read-only, lowest controversy, ships fastest, proves the rotation policy is paying off.
3. Approve R5 (council chamber live) — turns existing decisions.md into visible infrastructure, reinforces the "use the council in every step" standing order.
4. Approve R4 (security posture) only after R1 lands, so the posture panel can re-use the same `reauth-needed` copy and caveat-warning component.

R6, R7, R8 stay parked until R1–R5 are in production and the user has used them in anger.

## Files / scope touched (read-only verification)

- Read: `docs/PROJECT_MEMORY.md`, `docs/FEATURE_INVENTORY.md`, `docs/security-hardening-batch-a/{spec,decisions,tasks}.md`, `frontend-react/src/api/client.ts`, `frontend-react/src/contexts/ConnectionContext.tsx`.
- No files modified. This report is the only output.
