# Jarvis War Room Dashboard — Usage Guide v1.1.0
> Jarvis Company OS — Phase 2 Release

## Overview

The War Room Dashboard is the live nerve center of the Jarvis multi-agent system. It visualizes:
- **Agent constellation** — live 3D orbs showing each agent's health
- **Kanban board** — task ownership and status across all agents
- **Cost EKG** — real-time spend ribbon with color thresholds
- **Audit log strip** — scrolling security and event feed
- **Transcript viewer** — searchable Hermes session history
- **Discord Nexus** — auto-coordinated bot thread map
- **Achievement Theater** — XP/level-up notifications and badges

## Architecture

```
┌─────────────────────────────────────────┐
│  Browser → http://localhost:8503       │  SPA static server
│  ├── API calls → localhost:8502      │  FastAPI backend
│  └── WebSocket → localhost:8502/ws    │  Live push
└─────────────────────────────────────────┘
```

- **Static server** (`spa_server.py` on port 8503) — Serves `index.html` with SPA routing fallback
- **Backend** (FastAPI + uvicorn on port 8502) — REST API + WebSocket
- **Headscale** (port 8080) — Tailscale coordination server

## Authentication

All endpoints require a token. Development mode uses `token=dev` query parameter.

```bash
# Example: fetch agents
curl "http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1/dashboard/agents?token=dev"
```

**Production:** Set JWT cookie `jarvis-dashboard-token` or use `Authorization: Bearer <jwt>`.

## Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Plugin health | No |
| GET | `/dashboard/agents` | Live agent roster | Yes |
| GET | `/dashboard/tasks` | Kanban task list | Yes |
| GET | `/dashboard/cache` | Aggregated snapshot | Yes |
| GET | `/dashboard/memory` | Memory DNA helix data | Yes |
| GET | `/dashboard/metrics` | Prometheus-style metrics | Yes |
| GET | `/sessions` | Session list | Yes |
| GET | `/sessions/{id}` | Full transcript | Yes |
| GET | `/audit` | Audit log (redacted) | Yes |
| GET | `/audit/stream` | SSE line count | Yes |
| GET | `/discord/threads` | Discord thread cache | Yes |
| POST | `/discord/webhook` | Discord webhook receiver | HMAC sig |
| POST | `/kanban/task` | Create task | Yes |
| POST | `/nl-router` | Natural language dispatch | Yes |
| WS | `/ws?token=dev` | Live push channel | Yes |

## WebSocket Channels

Connect to `ws://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1/ws?token=dev`

```javascript
// Subscribe to channels after connect
{"subscribe": ["agents", "kanban", "audit", "metrics"]}

// Request full snapshot
{"request": "snapshot"}
```

Supported channels: `agents`, `kanban`, `audit`, `metrics`, `memory`, `sessions`, `discord`.

## Security Model

- **Auth enforced** on all endpoints except `/health`
- **No localhost fallthrough** — auth is mandatory everywhere
- **Audit redaction** — secrets scrubbed via `REDACTION_PATTERNS` before returning
- **XSS prevention** — all user-controlled text escaped via `escapeHtml()` before DOM insertion
- **Discord webhook** — HMAC-SHA256 signature verification required
- **WebSocket** — token validated BEFORE connection accept

## Files and Functions

### Backend

| File | Function | Purpose |
|------|----------|---------|
| `server.py` | `app = FastAPI()` | Entry point, router registration, lifespan |
| `core/data_aggregator.py` | `run()` | Periodic scan of agents, tasks, memory, decisions |
| `core/websocket.py` | `ConnectionManager` | Broadcasts updates to WS subscribers |
| `core/audit.py` | `log_action()` | Writes JSONL audit records |
| `api/sessions.py` | `list_sessions()`, `get_session_transcript()` | Read Hermes SQLite DB |
| `api/audit.py` | `get_audit()`, `audit_stream()` | Read/redact audit.jsonl |
| `api/discord_bridge.py` | `discord_webhook()`, `list_threads()` | Webhook receiver + thread cache |
| `auth/dependencies.py` | `get_current_user()`, `get_current_user_ws()` | Token/JWT validation |

### Frontend

| File | Function | Purpose |
|------|----------|---------|
| `index.html` | `updateAgents()`, `updateKanban()`, etc. | Main dashboard UI |
| `js/three-constellation.js` | `init3D()`, `update3D()` | Three.js 3D agent constellation |
| `js/theater.js` | `Theater.emit()`, `Theater.registerDef()` | Achievement toast system |
| `js/websocket-client.js` | `WsClient` | Auto-reconnect WS with fallback polling |
| `js/dna-helix.js` | `initDNA()`, `updateDNA()` | CSS 3D double-helix memory viz |

## systemd Services

```bash
# Status
sudo systemctl status jarvis-dashboard-backend
sudo systemctl status jarvis-dashboard-static
sudo systemctl status headscale

# Restart
sudo systemctl restart jarvis-dashboard-backend
sudo systemctl restart jarvis-dashboard-static

# Logs
sudo journalctl -u jarvis-dashboard-backend -f
sudo journalctl -u jarvis-dashboard-static -f
```

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `API_HOST` | `127.0.0.1` | Backend bind address |
| `API_PORT` | `8502` | Backend port |
| `AGGREGATE_INTERVAL` | `30` | Scan period in seconds |

## Headscale Configuration

File: `/etc/headscale/config.yaml`

Critical schema for v0.28.0:
```yaml
database:
  type: sqlite
  sqlite:
    path: /var/lib/headscale/db.sqlite   # NESTED, not flat

derp:
  server:
    enabled: true
    region_id: 999
    stun_listen_addr: "0.0.0.0:3478"
    automatically_add_embedded_derp_region: true
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `401` on all endpoints | Missing token | Add `?token=dev` |
| WS connects then closes | Wrong token | Check `TOKEN` in index.html |
| `/war-room` 404 | Plain http.server | Use `spa_server.py` for fallback |
| Headscale `DERPMap empty` | Missing DERP config | Add `derp.server` block |
| Headscale `database.path` | Flat schema | Use `database.sqlite.path` |
| Audit shows `[REDACTED]` | Secret detected | Normal — redaction working |

## Release Checklist

- [x] spec.md complete
- [x] plan.md complete
- [x] tasks.md complete
- [x] Build passes (all services active)
- [x] Smoke tests pass (12/12)
- [x] Security review passed (4 CRITICAL fixed)
- [x] Tutorial/docs complete (this file)
- [ ] Obsidian updated
- [ ] Excalidraw updated

---

## Army Operations Addendum — v1.4.0

Army Operations adds a Conductor-style CLI-worker deck inside the existing React War Room. Hermes remains the control plane; this panel is a profile-safe operator view.

### What it does

- Shows worker availability for Claude Code, Codex CLI, and MiniMax M3.
- Spawns dashboard-local run records.
- Captures per-run logs.
- Generates a workspace diff for review.
- Supports Approve, Reject with reason, and Rerun with feedback injection.
- Keeps `writes_profile_configs = false` for v1. Approval is a state mark only; it does not merge, push, or edit Hermes profiles.

### New backend file

| File | Function / class | Purpose |
|------|------------------|---------|
| `backend/api/army.py` | `router = APIRouter(prefix="/army")` | Registers Army Operations endpoints. |
| `backend/api/army.py` | `RunRequest` | Validates worker, task, repo, and dry-run payloads. |
| `backend/api/army.py` | `RunRecord` | Defines persisted run state. |
| `backend/api/army.py` | `_worker_roster()` | Detects `claude` and `codex` with `shutil.which`; keeps MiniMax planned/disabled. |
| `backend/api/army.py` | `_execute_run()` | Creates run workspace/log output. Uses dry-run by default and `subprocess.run(..., shell=False)` if real Claude execution is explicitly requested. |
| `backend/api/army.py` | `_safe_run_id()` / `_run_paths()` | Blocks path traversal and confines workspaces to dashboard state. |
| `backend/api/army.py` | `_redact()` | Scrubs secret-looking values from worker logs. |
| `backend/api/army.py` | `_unified_diff_for_workspace()` | Builds a unified diff from generated workspace files. |
| `backend/server.py` | `plugin.include_router(army_router)` | Mounts `/army/*` under the dashboard plugin API. |

### New frontend files and edits

| File | Function / type | Purpose |
|------|-----------------|---------|
| `frontend-react/src/components/ArmyOperations.tsx` | `ArmyOperations()` | Worker roster, run spawn form, run board, logs, diff viewer, approve/reject/rerun controls. |
| `frontend-react/src/types/dashboard.ts` | `ArmyWorker`, `ArmyRun`, `ArmyRunRequest` | Typed API payloads. |
| `frontend-react/src/api/client.ts` | `armyWorkers()`, `spawnArmyRun()`, `armyLogs()`, etc. | Typed client methods for the panel. |
| `frontend-react/src/App.tsx` | `<PanelSection id="army-operations">` | Adds the panel to the dashboard layout. |
| `frontend-react/src/components/commandMenuLinks.ts` | `army-operations` link | Makes the panel visible/toggleable in the command menu. |

### New tests

| File | Test | Purpose |
|------|------|---------|
| `tests/test_army_api.py` | `test_army_workers_report_available_and_unavailable_without_profile_writes` | Verifies roster shape and profile-safe contract. |
| `tests/test_army_api.py` | `test_army_dry_run_lifecycle_is_dashboard_local` | Verifies dry-run creation, logs, diff, and no profile mutation. |
| `tests/test_army_api.py` | `test_army_reject_and_rerun_preserve_feedback` | Verifies reject reason and rerun feedback injection. |
| `tests/test_army_api.py` | `test_army_rejects_path_like_run_ids` | Verifies path traversal defense. |
| `tests/test_army_api.py` | `test_army_approve_is_state_only_not_merge` | Verifies approve does not merge or write profiles. |

### New endpoints

All are mounted under `/api/plugins/jarvis-dashboard/v1` and require dashboard auth:

- `GET /army/workers`
- `GET /army/runs`
- `POST /army/runs`
- `GET /army/runs/{run_id}`
- `GET /army/runs/{run_id}/logs`
- `GET /army/runs/{run_id}/diff`
- `POST /army/runs/{run_id}/reject`
- `POST /army/runs/{run_id}/rerun`
- `POST /army/runs/{run_id}/approve`

### Verification commands used

```bash
/home/ubuntu/.hermes/hermes-agent/venv/bin/python3 -m pytest tests -q
npm run build
```

Runtime smoke started a no-access-log backend on port 8512 and Vite on 8513, then verified worker discovery, dry-run creation, logs, diff, approve state, and browser UI spawn.

---
*Jarvis Company OS — Phase 2 v1.1.0 + Army Operations v1.4.0*
