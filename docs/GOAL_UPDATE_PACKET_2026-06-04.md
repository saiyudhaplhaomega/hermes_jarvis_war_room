# /goal Update Packet — War Room Post-Batch-A Forward Motion

Status: COMPLETE — recommendations only, no runtime mutation
Created: 2026-06-04
Project: Jarvis War Room Dashboard
Owner: Jarvis
Source goal: docs/GOAL.md

## Executive Summary

Batch A is live and verified. Three scout perspectives were collected for the next useful War Room updates:

1. Security/Ops scout: completed via MiniMax M3 direct fallback; output captured in `/tmp/war-room-security-ops-scout.out`.
2. Product/UX scout: completed via MiniMax M3 direct fallback; it also created `docs/SCOUT_FINDINGS_2026-06-04_BATCH_A_PRODUCT_UX.md` despite the read-only prompt.
3. Architecture/Maintainability scout: completed via MiniMax M3 direct fallback; it also created `docs/SCOUT_SYNTHESIS_2026-06-04_ARCH_MAINTAINABILITY.md` despite the read-only prompt.

Important transparency note: the two scout-generated docs were created by the scouts, not by the planned synthesis step. They are useful artifacts but should be treated as pending Saiyudh keep/remove decision. No code, runtime, service, k3s, or system config mutation was performed during this `/goal` synthesis.

## Boss / Manager Interpretation

`/goal` is treated as a durable project-local goal artifact, not as a Hermes slash command. The Hermes Agent skill did not show `/goal` as a built-in slash command. The safe interpretation is: record the goal, collect scout recommendations, synthesize into an approval-ready packet, update Obsidian, and report finish.

## Verified Baseline

Batch A live state already verified before this packet:

- Backend service active on `127.0.0.1:8502`.
- Static SPA service active on `127.0.0.1:8503`.
- Query-token fallback rejected with `401` by default.
- REST bearer auth and WebSocket cookie auth passed live smoke.
- Localhost CORS allowed; public IP origin rejected.
- Boss/Security final verdict: PASS.

## Top Recommended Next Moves

### P0. Reconcile audit log path before installing logrotate

Source: Security/Ops scout + Architecture scout.

Finding:
- Logrotate candidate targets a dashboard-local audit path, but live evidence indicates audit writes may be going to `/home/ubuntu/.hermes/state/audit/audit.jsonl`.
- Installing logrotate before reconciling the true write path could create false protection: logrotate rotates a file that is not actually growing.

Why it matters:
- This directly connects to the VPS disk pressure question.
- It is an ops hygiene issue, not a feature.

Required before action:
- Spec clarification or decision note naming the canonical audit log path.
- Boss/Ops review before any `/etc/logrotate.d` install.

Acceptance idea:
- A test or smoke proves the logrotate candidate targets the real audit file.
- `logrotate --debug` validates the corrected candidate.
- Optional forced rotation only after Saiyudh approval.

### P1. Build a real `/ready` contract

Source: Security/Ops scout + Architecture scout + Product/UX scout.

Finding:
- `/ready` currently exists, but the useful future state is a structured readiness body with backend, cache, kanban DB, audit log, websocket/auth, and version state.
- Product UX depends on this to explain failures instead of showing a vague connection dot.

Why it matters:
- This is the highest-leverage diagnostic foundation for War Room.
- It turns “not working” into visible system state.

Required before coding:
- Mini-spec for readiness schema and degraded semantics.
- Boss/security review because readiness must not leak secrets or sensitive paths beyond what is acceptable.

Acceptance idea:
- Authenticated `/ready` returns structured component statuses.
- Simulated degraded dependencies flip appropriate fields to degraded.
- No token or secret appears in response.

### P1. Connection and conversational UX Batch B

Source: Product/UX scout.

Recommended combined spec:
- `docs/connection-and-conversational-ux-batch-b.md`

Scope:
- Replace single connection dot with a 4-state adaptive banner:
  - `open`
  - `bootstrap`
  - `reauth-needed`
  - `backend-not-ready`
- Add re-auth action using `POST /auth/session`.
- Add local frustration/intent-shift detection:
  - `aaaaaa`
  - `no idea`
  - `isn't working`
  - repeated failed attempts
- Switch from answer mode to diagnose mode when frustration is detected.
- Surface `/health` + `/ready` inline when user says something is broken.

Why it matters:
- This directly satisfies Saiyudh’s stated UX requirement: full-page adaptive conversational experience, not rigid template loops.

Required before coding:
- Product spec + acceptance tests.
- Preserve protected DOM contracts: `chat-thread`, `nl-input`, project/session IDs.

Acceptance idea:
- Invalid session shows `reauth-needed` and buffers input.
- Typing `aaaaaa` flips to diagnose mode.
- Typing a normal question does not false-trigger.

### P1. Resolve SPA token-in-HTML caveat

Source: Security/Ops scout.

Finding:
- Batch A removed tokens from REST and WS URLs, but the SPA still has a documented token-in-runtime-config caveat.

Why it matters:
- Safe on loopback, but dangerous if anyone tunnels or externally exposes the SPA.

Required before coding:
- New security mini-spec choosing a bootstrap contract.
- Boss/security review.

Acceptance idea:
- `curl http://127.0.0.1:8503/war-room` does not contain the token value.
- Auth bootstrap still works.
- WS cookie auth still works.

### P2. Audit Replay view

Source: Product/UX scout.

Scope:
- Full-page read-only audit replay, project-scoped by default.
- Filters by project, agent, event type, and time range.
- Expandable redacted JSON rows.

Why it matters:
- Gives the War Room memory and visible operational history.
- Low runtime risk if read-only.

Required before coding:
- Spec for route, filters, redaction, pagination, and project scoping.

Acceptance idea:
- `/war-room/audit` loads.
- Filtering narrows rows.
- Token/API-key fields are absent or redacted.

### P2. Council Chamber full page

Source: Product/UX scout.

Scope:
- Surface Boss/Manager/Secretary verdicts and decisions in a dramatic full-page view.
- Read existing decision docs, especially Batch A decisions.
- Add “challenge this decision” affordance only after spec approval.

Why it matters:
- Makes the “use council every step” operating rule visible inside the War Room.

Required before coding:
- Spec for decision source of truth, UI, and Kanban challenge-card creation.

Acceptance idea:
- Page lists DEC-001..DEC-009 with correct status.
- Challenge flow creates a project-scoped Kanban card only after confirmation.

### P2. Version-control and release hygiene

Source: Architecture/Maintainability scout.

Finding:
- Batch A work is verified but uncommitted.
- Manifest still reports `1.1.0` while tutorial addendum labels Batch A as `v1.5.0`.
- Root specs and Batch A specs are not fully cross-linked.

Why it matters:
- A verified release should become a clean, reversible audit trail.

Required before action:
- Saiyudh approval on commit policy and version bump.

Acceptance idea:
- Either one squashed Batch A commit or 4 logical commits.
- `git status` clean after commit.
- Manifest/Tutorial version strings agree.

### P3. Service artifact canonicalization

Source: Security/Ops scout + Architecture scout.

Finding:
- Root and `systemd/` service artifacts both exist and are currently safe.
- Duplication creates drift risk.

Required before coding/action:
- Decide canonical source path and install workflow.

Acceptance idea:
- Tests still assert all service artifacts bind localhost and disable access logs.
- `systemctl cat` confirms installed units came from the canonical artifact.

## Recommended Approval Order

1. Audit log path reconciliation first, because it affects disk safety and blocks safe logrotate install.
2. Real `/ready` contract, because multiple UX/security ideas depend on it.
3. Connection + conversational UX Batch B, because it directly addresses the user experience requirement.
4. SPA token-in-HTML caveat, because it closes the biggest remaining Batch A caveat.
5. Audit Replay and Council Chamber as dramatic full-page War Room upgrades.
6. Version/commit hygiene once Saiyudh approves commit structure.

## Items Explicitly Not Applied

- No code changes.
- No service restarts.
- No logrotate install.
- No k3s mutation.
- No gateway mutation.
- No dependency installation.
- No commit/tag/version bump.

## Artifacts Created During `/goal`

Intended artifacts:
- `docs/GOAL.md`
- `docs/GOAL_UPDATE_PACKET_2026-06-04.md`

Scout-generated artifacts requiring Saiyudh keep/remove decision:
- `docs/SCOUT_FINDINGS_2026-06-04_BATCH_A_PRODUCT_UX.md`
- `docs/SCOUT_SYNTHESIS_2026-06-04_ARCH_MAINTAINABILITY.md`

Temporary scout outputs:
- `/tmp/war-room-security-ops-scout.out`
- `/tmp/war-room-product-ux-scout.out`
- `/tmp/war-room-architecture-scout.out`

## Closeout Status

This packet completes the `/goal` synthesis step. The next safe action is not coding; it is Saiyudh choosing which recommendation becomes the next spec package.
