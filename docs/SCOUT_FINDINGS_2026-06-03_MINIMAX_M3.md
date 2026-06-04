# MiniMax M3 Scout Findings — War Room Archive

Timestamp: 2026-06-03T21:26:36+08:00
Scope: Hermes War Room dashboard and Jarvis/Hermes runtime boundary
Sources:
- `/tmp/minimax-m3-war-room-scouts/direct/scout1.md`
- `/tmp/minimax-m3-war-room-scouts/direct/scout2.md`
- `/tmp/minimax-m3-war-room-scouts/direct/scout3.md`

Status: archived for planning only. No recommendations in this report were auto-applied to dashboard code or runtime.

## Executive summary

The MiniMax M3 scouts found one active runtime fault, several protected frontend contracts, and a set of planning/security candidates for future War Room work.

The active Kanban dispatcher fault has since been resolved by separating Hermes runtime Kanban from the War Room/user Kanban database:

- War Room/user DB remains: `/home/ubuntu/.hermes/kanban.db`
- Hermes runtime dispatcher DB now uses: `/home/ubuntu/.hermes/hermes-kanban.db`
- Active gateway processes now carry: `HERMES_KANBAN_DB=/home/ubuntu/.hermes/hermes-kanban.db`

## Findings archived from Scout 1

### 1. Kanban dispatcher failure

Original evidence:

- Gateway journal reported `sqlite3.OperationalError: no such column: status`.
- Trace pointed to `hermes_cli/kanban_db.py` during `connect()` on board `default`.

Archived resolution:

- Do not migrate `/home/ubuntu/.hermes/kanban.db` to satisfy Hermes dispatcher schema.
- Preserve that file as the War Room/user/company Kanban DB.
- Use a separate Hermes runtime DB via `HERMES_KANBAN_DB`.

Current verification after fix:

- Hermes DB `/home/ubuntu/.hermes/hermes-kanban.db` exists.
- `PRAGMA integrity_check` returned `ok`.
- `task_runs` includes `status` and `claim_lock`.
- Gateway logs no longer show the `status` column error after the dispatcher tick window.
- War Room backend and SPA remained healthy.

### 2. Health vs readiness split

Scout noted that runtime liveness could pass while functional readiness was degraded. This is valid as a future improvement:

- Keep lightweight `/health` for process liveness.
- Add a readiness check that includes project Kanban cache, DB connectivity, dashboard token alignment, and SPA proxy health.

No implementation was done during this archive.

### 3. Roadmap visibility

Scout flagged that Phase 1 infrastructure exists while P0-P8 platform work remains mostly pending. Future dashboard planning should surface P0-P8 status in an executive ticker or planning panel, but only after spec/plan/tasks review.

### 4. High-risk mode router surface

Scout flagged `backend/api/mode_router.py` as a large critical-path file for chat routing. Treat this as a refactor candidate, not an immediate change. Any split requires:

1. Founder/Boss discussion.
2. `spec.md`, `plan.md`, `tasks.md` update.
3. Smoke tests for all chat modes.
4. Security review.

### 5. Protected frontend DOM contracts

Scout confirmed these DOM IDs as live/protected surfaces:

- `chat-thread`
- `nl-input`
- `project-select`
- `kanban-board`
- `audit-stream`

Do not rename these without a recorded decision and full JS reference update.

### 6. Protected frontend modules

Scout confirmed these frontend modules as protected:

- `frontend/public/js/theater.js`
- `frontend/public/js/dna-helix.js`
- `frontend/public/js/three-constellation.js`
- `frontend/public/js/websocket-client.js`

Change-control is required for visual/realtime stack edits.

## Findings archived from Scout 2

Scout 2 recommended updates to:

- `docs/PROJECT_MEMORY.md`
- `docs/FEATURE_INVENTORY.md`
- War Room skill/reference docs
- Obsidian/Jarvis memory

Accepted archive actions:

- This report was created.
- `PROJECT_MEMORY.md` now links to this report.
- `FEATURE_INVENTORY.md` now records the Hermes-vs-War-Room Kanban separation and protected scout findings.
- Obsidian Scout Reports and a decision note were updated.

Important correction:

- Scout 2 listed the Kanban `status` error as unfixed at the time of generation. It is now resolved by separation, not by migrating the War Room DB.

## Findings archived from Scout 3

Scout 3 produced a partial/truncated runtime advisory. Usable findings:

### Reliability candidates

- Consider adding SPA health/readiness coverage for port 8503.
- Confirm dashboard processes are supervised and restartable.
- Consider increasing SPA server backlog if public or health-check traffic increases.

### Security candidates

- Keep localhost-only assumption documented.
- Verify auth posture before any public bind change.
- Verify Ollama Cloud API key handling remains secret and never logged.
- Review CORS policy before external exposure.

Rejected/modified recommendation:

- Scout suggested dropping `--no-access-log` for observability. This conflicts with War Room security policy: backend uvicorn access logs must remain disabled because query-token URLs can leak into logs. If observability is needed, implement redacted structured logs, not raw access logs.

Truncation note:

- `scout3.md` ends abruptly at line 19 (`SPA bundle is 781...`). No missing content was inferred.

## Next-step candidates requiring separate approval

These are not approved for implementation by this archive:

1. Add readiness endpoint distinct from liveness.
2. Add SPA health probe for 8503.
3. Add redacted observability for dashboard backend without query-token leakage.
4. Create a P0-P8 roadmap status panel/ticker.
5. Plan a safe `mode_router.py` decomposition.
6. Add secret-handling verification for Ollama Cloud/API provider config.

## Guardrail

Scout agents may recommend; they must not auto-apply. Every item above requires Saiyudh approval, Boss/Manager review as appropriate, and the normal Spec Kit/release gates before implementation.
