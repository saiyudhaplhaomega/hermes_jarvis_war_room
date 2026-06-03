# Phase 2 Technical Plan

## 1. Architecture Overview

```
Phase 1 (current)
  Frontend: static HTML (index.html) ──→  Backend: FastAPI ──→ SQLite / flat files

Phase 2 (target)
  Frontend: enhanced HTML with Three.js + WebSocket client ──→
  Backend: FastAPI + native /ws endpoint ──→
  Data: Hermes SQLite (sessions) + audit JSONL + new achievements.json

+ Discord Webhook listener (optional local bot bridge)
+ systemd services (x2: backend + frontend-static)
+ Headscale VPN (infra)
```

## 2. File Structure After Phase 2

```
jarvis-dashboard/
├── manifest.json                    # updated to v1.1.0
├── docs/
│   ├── spec.md
│   ├── plan.md
│   └── tasks.md
├── backend/
│   ├── server.py                  # adds /ws endpoint, Three.js route
│   ├── requirements.txt           # no new deps (websockets built into FastAPI)
│   ├── core/
│   │   ├── config.py              # unchanged
│   │   ├── data_aggregator.py     # adds websocket broadcast hook
│   │   ├── models.py              # adds WebSocketMessage, Achievement models
│   │   └── audit.py               # adds read_logs() function
│   ├── api/
│   │   ├── cache.py               # adds session/transcript endpoints
│   │   ├── kanban.py              # unchanged
│   │   ├── nl_router.py           # unchanged
│   │   ├── sessions.py            # NEW — session list + transcript
│   │   ├── audit.py               # NEW — audit log API
│   │   └── discord_bridge.py      # NEW — webhook receiver
│   └── auth/
│       └── dependencies.py        # adds ws_token_verify helper
├── frontend/
│   └── public/
│       ├── index.html             # EXPANDED — all new panels+
│       ├── three-constellation.js # NEW — Three.js scene
│       ├── theater.js             # NEW — achievement system
│       ├── websocket-client.js    # NEW — WebSocket multiplexing
│       └── dna-helix.js         # NEW — 3D CSS helix
└── systemd/
    └── jarvis-dashboard.service
```

## 3. Technology Choices

| Component | Tech | Reason |
|-----------|------|--------|
| 3D Engine | **Three.js via CDN** | No build step, CDN cached, widely used |
| WebSocket | **Native WS (no socket.io)** | FastAPI has native `WebSocket`, reduces deps |
| State Sync | **Broadcast from aggregator** | Aggregator already runs every 30s; triggers push |
| Discord | **Incoming webhooks** | Reuses existing skill, no gateway complexity |
| Achievements | **JSON persistence** | No DB needed, human-readable |
| Motions | **Wiring Three.js canvas inside existing HTML** | Maintains single-file deployability |
| CSS | **Tailwind + custom CSS** | Already in use, sufficient |

## 4. Data Flow for WebSocket Push

```
Aggregator.run()          WebSocketManager          Frontend
     │                          │                      │
     ├── scan tasks ────────────┤                      │
     ├── scan agents ───────────┤                      │
     └── scan memory ───────────┤                      │
     → new state ───────────────→ broadcast(json) ──→ update panel
```

`core/websocket.py` (new) manages `ConnectionManager` that holds all active WebSocket connections. Each connection subscribes to one or more channels: `agents`, `kanban`, `memory`, `metrics`, `audit`, `transcripts`.

## 5. Backend Changes

### 5.1 `/ws` endpoint
Path: `/api/plugins/jarvis-dashboard/v1/ws`
- Establish WS connection.
- Accept subscription message: `{"subscribe": ["agents", "kanban"]}`.
- On aggregator update, broadcast to matching subscriptions.
- On demand: `{"request": "sessions", "limit": 10}` returns top 10 sessions.

### 5.2 Session API
Path: `GET/POST /api/plugins/jarvis-dashboard/v1/sessions`
- `GET /sessions?limit=20&offset=0` -> list of session summaries.
- `GET /sessions/{id}/transcript` -> full transcript (messages array).
- `POST /sessions/{id}/replay` -> mock step-through for playback.

### 5.3 Audit API
Path: `GET /api/plugins/jarvis-dashboard/v1/audit`
- `GET /audit?severity=error&since=2026-05-29T00:00:00`
- Returns 200 lines max, paginated. Supports SSE streaming.

### 5.4 Discord Bridge (Webhook)
Path: `POST /api/plugins/jarvis-dashboard/v1/discord/webhook`
- Receives Discord webhook JSON, normalizes, stores in memory cache.
- Frontend subscribes to `discord` channel over ws for push.

## 6. Frontend Changes

### 6.1 Script Modules (loaded via <script src=...>)
- **three-constellation.js** — initializes Three.js scene, agent orbs, connections, camera orbit controls, bloom post-proc (using UnrealBloomPass or simple additive blending).
- **websocket-client.js** — class `WsClient`, auto-reconnect with exponential back-off, message routing to callbacks per channel.
- **theater.js** — class `AchievementTheater`, toast queue, SVG badge rendering, confetti canvas.
- **dna-helix.js** — CSS 3D transforms for double helix (lighter than Three.js for this element).

### 6.2 Panel Integration
- All existing `updateX()` functions in index.html refactored to also notify the theater on state changes (e.g., first kanban card moved triggers "First Dispatch" achievement).
- Add global `window.dashboardConfig` object for CDN URLs, WS endpoint.
- New bottom drawer for transcripts: fixed div that slides up from bottom-right.
- New bottom bar for audit stream: fixed footer strip with live scrolling log lines.

## 7. Infra Changes

### 7.1 Systemd Service
- Unit `jarvis-dashboard.service`: runs backend uvicorn on :8502.
- Shell wrapper manages venv activation + working directory.
- `jarvis-dashboard-static.service`: runs frontend static server on :8503.
- Install script: `sudo cp *.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable jarvis-dashboard --now`

### 7.2 Headscale Config
- Switch from top-level `ip_prefixes` to structured `prefixes` block:
  ```yaml
  prefixes:
    v4: 100.64.0.0/10
  ```
- Verify with `headscale serve` and test registration of a mock node.
- Register dashboard as Tailnet service.

## 8. Performance Budget
- < 100ms first paint.
- < 5 MB total download (Three.js is ~600 KB gzipped over CDN).
- < 50 MB RAM for backend process.
- < 60 fps for Three.js scenes.
- Backend < 10% CPU at idle, < 30% during aggregator burst.

## 9. Security
- WebSocket endpoint still requires auth token in query param on handshake.
- websocket-client.js passes `?token=dev` on ws connect.
- Audit log viewer only readable if `metrics_read` permission present.
- Session transcripts scrubbed: tool output stripped if it might contain secrets.

## 10. Rollback Plan
- Tag Phase 1: git tag in plugin dir?
- Actually, we have no git repo for this plugin.
- Risk mitigation: copy entire `~/.hermes/profiles/jarvis/plugins/jarvis-dashboard` to `plugins/jarvis-dashboard-backup` before any destructive edits to existing files.
- Keep `index.html` as `index-backup.html` in parallel.

## 12. Premium Mission Control + Role Overlay Plan

### 12.1 Backend
- `backend/api/roles.py` exposes dashboard-local `/roles`, `/models`, and `/roles/test` endpoints.
- Role mappings persist to `~/.hermes/state/dashboard/role_mappings.json` unless overridden by `JARVIS_DASHBOARD_ROLE_MAPPINGS` in tests.
- Pydantic validation rejects path-like agent identifiers and unknown status values.
- The route declares `writes_profile_configs: false` and never imports or writes profile config mutation helpers.

### 12.2 Frontend
- `MissionControlOverview.tsx` adds the premium overview command deck.
- `RoleMatrix.tsx` adds the dynamic role/model mapping UI.
- `DashboardHeader.tsx` adds premium branding, v1.3 badge, live clock, profile-safe status, and Chat/Dashboard nav.
- Existing dashboard panels remain in `App.tsx` after the new overview and role matrix.

### 12.3 Project Scope Stability
- `DashboardContext.refresh()` remembers the latest explicit project slug and uses it for interval polling. This prevents project-scoped panels from drifting back to global data after the first refresh.

### 12.4 Verification
- Backend route tests: `python -m pytest tests/test_roles_api.py -q`.
- Frontend build: `npm run build`.
- Runtime smoke: `scripts/smoke_premium_dashboard.py` verifies 8502, 8503, `/roles`, `/models`, and `/war-room`.
- Security scan: search for profile config writes, hardcoded secrets, eval/exec, shell injection, and unsafe path writes.

- [ ] Dashboard loads at http://127.0.0.1:8503 with all old panels intact.
- [ ] Three.js constellation renders in < 3s, orbits, camera responds.
- [ ] WebSocket connection established and receives at least one push within 35s.
- [ ] "First Dispatch" toast appears on first kanban interaction.
- [ ] Transcript viewer lists at least one past session.
- [ ] Audit bar shows a log line with color matching severity.
- [ ] Headscale starts without error, log shows "listening" and "ephemeral node".
- [ ] systemd status shows both services active.

---
APPROVED BY: Council

---

## 13. Army Operations Technical Plan

### 13.1 Backend Architecture

Add `backend/api/army.py` as the dashboard-local orchestrator API. It owns:

- safe worker discovery using `shutil.which`,
- run state persistence in dashboard-owned JSON under `DASHBOARD_DATA`,
- per-run workspaces under a dashboard-owned runs directory,
- log capture to per-run text files,
- unified diff generation from files in each run workspace,
- non-destructive approve/reject/rerun state transitions.

The v1 runner is intentionally conservative. It does not mutate Hermes profiles and does not merge branches. It can create a run workspace and capture output. Approval marks state and records a gate packet; later phases may attach PR creation after explicit approval.

### 13.2 Endpoint Contract

Mounted under `/api/plugins/jarvis-dashboard/v1`:

- `GET /army/workers` -> worker roster and availability.
- `GET /army/runs` -> all run summaries.
- `POST /army/runs` -> create a run request.
- `GET /army/runs/{run_id}` -> run detail.
- `GET /army/runs/{run_id}/logs` -> captured log text.
- `GET /army/runs/{run_id}/diff` -> unified diff for workspace files.
- `POST /army/runs/{run_id}/reject` -> mark rejected and save reason.
- `POST /army/runs/{run_id}/rerun` -> create a new run with prior feedback included.
- `POST /army/runs/{run_id}/approve` -> mark approved only; no merge/push in v1.

Every response must include or preserve `writes_profile_configs: false` where relevant.

### 13.3 Frontend Architecture

Add `ArmyOperations.tsx` and wire it into `App.tsx` as a normal dashboard panel. Extend `types/dashboard.ts` and `api/client.ts` with typed Army Operations payloads.

The panel contains:

- worker roster cards,
- create-run form,
- run board table,
- selected run detail,
- log pane,
- diff pane,
- approve/reject/rerun controls.

### 13.4 Test Strategy

TDD order:

1. Add failing backend API tests for worker discovery, safe run creation, path traversal rejection, reject/rerun, and profile-safe contract.
2. Implement backend until tests pass.
3. Add frontend types/client/component and run TypeScript build.
4. Add runtime smoke script for health, worker roster, create dry run, list runs, logs, diff, and `/war-room` availability.

### 13.5 Rollback

Because this plugin is not a git repo, keep changes additive. If rollback is needed, remove `backend/api/army.py`, `ArmyOperations.tsx`, and the small router/client/type/App wiring. Dashboard-local state lives outside source files and can be deleted independently.
