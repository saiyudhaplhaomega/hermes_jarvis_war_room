# War Room Feature Inventory

<!-- AUTO-GUARDRAIL: Any agent touching frontend/public/index.html, frontend/public/js/, backend API routes, or systemd dashboard units MUST read this file first. -->
<!-- DO NOT remove or rename any feature marked [PROTECTED] without a new entry in docs/decisions.md and a backup snapshot. -->

Scope: Hermes War Room only: `/home/ubuntu/.hermes/profiles/jarvis/plugins/jarvis-dashboard`.
Do not use Skin Lesion/XAI project context for this dashboard.

Source contract: Jarvis Agent Platform Spec Package 00-04 supplied by Saiyudh on 2026-06-03.
Council recovery reference: `/tmp/claude-war-room-recovery.md` and Codex manager verification from the same recovery session.

## Project-Wise Setup Contract

Saiyudh's War Room setup is project-wise.

1. Projects are the active working context in the dashboard.
2. Agent setup, adding new agents, role/model assignments, skill feeding, tasks, runs, workspaces, and memory must be scoped to the selected project unless Saiyudh explicitly marks something as company/global.
3. The War Room may show cross-project/company-wide summaries, but mutations must default to the active project.
4. New-agent onboarding must ask or infer the target project first; never silently add agents to a global/default pool.
5. The project selector and active workspace indicator are protected infrastructure, not cosmetic UI.
6. Skin Lesion/XAI project context is not War Room context and must not be used for War Room implementation.

## Current Spec Phase

Current implementation is an incremental War Room dashboard, not the full P0-P8 platform yet.

Implemented / partially implemented:
- Dashboard shell and War Room live UI.
- Agent constellation, memory visualization, cost/audit ribbons.
- Dispatch/chat terminal.
- Project-aware Kanban task view.
- Workspace clone/remove panel.
- Session drawer.
- Army Operations backend API.
- Role Matrix backend API.
- `jarvis_company_os` backend modules for registry, ACL, budgets, hiring, routing, and schema scaffolding.

Pending / must not be faked:
- True topology canvas with companies/teams/agents/edges editing.
- Issues board as the canonical coordination primitive.
- Inbox for hire requests, blockers, merge approvals, and budget escalations.
- Runs/review UI with logs/diffs/approve/reject wired into the live HTML UI.
- Routines UI.
- Budget analytics panel.
- Full NATS/JetStream or equivalent bus integration if/when we move beyond v0.

## Protected Frontend Panels

| Panel | DOM id(s) | Key JS | Status | Protection |
|---|---|---|---|---|
| XP / Achievement Theater | `xp-bar`, `xp-text` | `Theater.renderBar`, `Theater.addXP` | [PROTECTED] | Engagement layer; do not delete `js/theater.js`. |
| Agent Constellation | `constellation`, `agent-list` | `updateAgents`, `init3D`, `update3D` | [PROTECTED] | Dramatic 3D agent view; user explicitly wants War Room visuals. |
| Memory DNA Helix | `dna-helix`, `mem-*` | `updateMemory`, `initDNAHelix` | [PROTECTED] | Memory visualization. |
| EKG Cost Ribbon | `ekg-panel`, `ekg-svg`, `cost-today` | `drawEkg`, `updateMetrics` | [PROTECTED] | Cost/spend telemetry. |
| Kanban Fleet | `kanban-board`, `kanban-count`, `kanban-project-label` | `updateKanban` | [PROTECTED] | Project-filtered board with stale/dependency/progress badges. |
| Dispatch Terminal | `chat-thread`, `mode-select`, `project-select`, `nl-input` | `sendChat`, `renderThread`, `loadModes`, `loadProjects` | [PROTECTED] | `chat-thread` is the live id. Do not revert blindly to `chat-history`. |
| Session Drawer | `session-drawer`, `session-list`, `session-search` | `toggleDrawer`, `loadSessions` | [PROTECTED] | Conversation review surface. |
| Audit Strip | `audit-strip`, `audit-stream` | `pollAudit` | [PROTECTED] | Fixed bottom audit timeline. |
| Discord Nexus | `discord-panel`, `discord-count` | `updateDiscord` | [PROTECTED] | Gateway/thread visibility. |
| Council Chamber | `council-panel` | placeholder/live future hooks | [PROTECTED] | Council visibility is core Jarvis UX. |
| Decision Log | `decisions-list` | `updateDecisions` | [PROTECTED] | Architecture/decision memory. |
| GitHub Workspace | `workspace-list`, `ws-url`, `ws-name` | `loadWorkspaces`, `cloneWorkspace`, `removeWorkspace` | [PROTECTED] | Worktree/workspace control. Only one definition of each workspace function is allowed. |
| Voice I/O | `mic-btn`, `nl-input` | `Voice.toggle`, `Voice.sendToAgent`, `sendChat` | [PROTECTED] | Voice-to-agent must target `nl-input`, not nonexistent `cmd-input`. |
| Connection Indicator | `conn-dot`, `conn-text` | `setConn` | [PROTECTED] | Shows WS/POLL/OFF status. |

## Protected JS Modules

| File | Export/API | Purpose | Protection |
|---|---|---|---|
| `frontend/public/js/websocket-client.js` | `WsClient` | WebSocket client with auto-reconnect and poll fallback. | [PROTECTED] |
| `frontend/public/js/theater.js` | `Theater` | XP, badges, confetti, audio chime. | [PROTECTED] |
| `frontend/public/js/dna-helix.js` | `initDNAHelix(id)` | CSS 3D memory double helix. | [PROTECTED] |
| `frontend/public/js/three-constellation.js` | `init3D`, `update3D`, `dispose3D` | Three.js agent constellation. | [PROTECTED] |

## DOM Element ID Contracts

Never rename these IDs without updating every JS reference and this inventory.

| ID | Used by |
|---|---|
| `chat-thread` | `loadProjects`, `onProjectChange`, `loadProjectSessions`, `renderThread` |
| `nl-input` | `sendChat`, `Voice.sendToAgent` |
| `mode-select` | `onModeChange`, `loadModes` |
| `project-select` | `onProjectChange`, `loadProjects` |
| `workspace-list` | `loadWorkspaces` |
| `xp-bar` | `Theater.renderBar` |
| `dna-helix` | `initDNAHelix` |
| `constellation` | `init3D` |
| `kanban-board` | `updateKanban` |
| `session-drawer` | `toggleDrawer` |
| `audit-stream` | `pollAudit` |

Known recovery invariant from 2026-06-03:
- `chat-history` existed in v1.1.0 backup but live UI uses `chat-thread`.
- Old references to `chat-history` caused UI crashes and must not be reintroduced unless the DOM is restored consistently.

## Backend API Contracts

| Endpoint family | Module | Writes Hermes profile config? | Status | Protection |
|---|---|---:|---|---|
| `/api/plugins/jarvis-dashboard/v1/dashboard/cache` | `backend/api/cache.py` | No | [PROTECTED] | Main data cache for UI. |
| `/api/plugins/jarvis-dashboard/v1/project/*` | project routes in `backend/server.py` / APIs | No | [PROTECTED] | Project selector and project-scoped task state. |
| `/api/plugins/jarvis-dashboard/v1/sessions/*` | `backend/api/sessions.py` | No | [PROTECTED] | Conversation drawer. |
| `/api/plugins/jarvis-dashboard/v1/audit*` | `backend/api/audit.py` | No | [PROTECTED] | Audit strip and audit view. |
| `/api/plugins/jarvis-dashboard/v1/army/*` | `backend/api/army.py` | No | [PROTECTED] | Army Operations backend; approval is a state flag only. |
| `/api/plugins/jarvis-dashboard/v1/roles`, `/models` | `backend/api/roles.py` | No | [PROTECTED] | Dashboard-local role/model overlay only. |
| `/api/plugins/jarvis-dashboard/v1/ws` | `backend/core/websocket.py` | No | [PROTECTED] | WS firehose; auth required. |

## Spec Package Contracts to Preserve

1. Node ≠ Agent. Never collapse runtime nodes and logical agents in UI, API, or schema.
2. Issue is the coordination primitive. Every real task/run must link to an issue when the issue layer is active.
3. Heartbeat wake cycle is not liveness ping. Keep labels distinct.
4. Every future agent should have SOUL.md, HEARTBEAT.md, TOOLS.md, and AGENTS.md; Agent Cards are generated from them.
5. `authorize(from, to, type)` is central and unit-tested before real bus routing is trusted.
6. Budgets are enforced at task assignment, worker spawn, hire, and wake cycle.
7. Hiring is board-approved by default and capped by headcount, budget, and recursion/depth.
8. Audit is append-only. Do not hide approvals, denials, hires, budget events, or control messages.
9. Artifacts are references only. Do not push blob payloads through the bus envelope.
10. No direct push to main; coding agents work in isolated worktrees and require review gates.

## Active Safety Invariants

1. No function may be defined more than once in `frontend/public/index.html`.
2. `shell=True` is banned in backend subprocess calls.
3. Dashboard role/model mapping must not mutate Hermes profile config, SOUL files, or `.env`.
4. Army run approval must not apply/push/merge code on the host without a separate explicit approval flow.
5. Token/secret scrub must run on logs before storage/API return.
6. Uvicorn access logs should stay disabled for dashboard backend because query-token URLs can leak into logs.
7. If Cloudflare quick tunnel is used, treat the URL as temporary and rotating.
8. Any UI file recovery must start by copying a timestamped backup.

## Versioning / Recovery Snapshots

| Version | Snapshot file | Notes |
|---|---|---|
| v1.1.0 | `frontend/public/index.html.v1.1.0-backup` | Baseline backup with `chat-history`. |
| pre-recovery | `frontend/public/index.html.pre-recovery-<timestamp>` | Must be created before recovery edits. |
| current | `frontend/public/index.html` | Live static UI served by `spa_server.py` on port 8503. |

## Runtime / Service Contracts

| Contract | Required value | Reason | Smoke coverage |
|---|---|---|---|
| Backend service | `jarvis-dashboard.service` on `127.0.0.1:8502` | API is private behind SPA proxy. | `smoke_runtime_config.py`, systemd/socket check |
| Static service | `jarvis-dashboard-static.service` runs `spa_server.py`, not `python -m http.server` | Needed for `/war-room`, injected runtime config, CSP/security headers, and API proxy. | `smoke_runtime_config.py` |
| Static bind | `127.0.0.1:8503` | Cloudflare tunnel is the public path; local port should not bind all interfaces. | socket check |
| Runtime token | `state/dashboard.env`, mode `600`, referenced by both systemd units | Prevents empty-token UI and avoids printing/seeding token in source. | `smoke_runtime_config.py` |
| Frontend API base | `window.__CONFIG__.API_BASE` / same-origin `/api/plugins/jarvis-dashboard/v1` | Must work locally and through Cloudflare; no hardcoded public backend IP. | `smoke_premium_dashboard.py` |
| CSP | Allows existing Tailwind/CDNJS/font origins only | Prevents CDN breakage while keeping a restricted policy. | browser render + console check |

## Known Broken Items Found During 2026-06-03 Recovery

| ID | Symptom | Root cause | Fix status |
|---|---|---|---|
| BUG-001 | Project selector / UI JS crash | Old JS references `chat-history`, but live DOM uses `chat-thread`. | Fixed 2026-06-03; smoke forbids `chat-history`. |
| BUG-002 | Voice transcription does not send | `Voice.sendToAgent` targets nonexistent `cmd-input` and `cmd-send`. | Fixed 2026-06-03; voice targets `nl-input` and calls `sendChat()`. |
| BUG-003 | Workspace polling duplicated / confusing | Duplicate definitions of `loadWorkspaces`, `cloneWorkspace`, `removeWorkspace` and duplicate interval. | Fixed 2026-06-03; smoke requires one definition. |
| BUG-004 | Project-filtered Kanban flickers or resets on WS updates | WS snapshot/all handlers call `updateKanban` without `ACTIVE_PROJECT`. | Fixed 2026-06-03; calls preserve `ACTIVE_PROJECT`. |
| BUG-005 | Auth endpoints reject UI when dev token not injected | systemd services did not set `JARVIS_DASHBOARD_DEV_TOKEN`; `spa_server.py` injected empty token if unset. | Fixed 2026-06-03; shared env file wired to both units. |
| BUG-006 | Browser fetches fail through Cloudflare/local page | Live HTML ignored `window.__CONFIG__`, hardcoded `43.131.26.109:8502` and `TOKEN=dev`. | Fixed 2026-06-03; API helper uses same-origin `apiUrl()`. |
| BUG-007 | 3D constellation can throw when Three.js is blocked | CSP/CDN failure left `THREE` undefined. | Fixed 2026-06-03; CSP allowlist updated and JS has graceful fallback. |

## How to Use This Document

Before editing any protected item:
1. Read this file.
2. Confirm the feature still exists in current code.
3. Take a timestamped backup.
4. If removing or renaming anything, add a decision to `docs/decisions.md` first.
5. Patch one thing at a time.
6. Run smoke tests and browser console checks.
7. Update this file with the new status.
