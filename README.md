# hermes_jarvis_war_room

Hermes/Jarvis War Room dashboard snapshot.

This repository preserves the current War Room implementation so the dashboard, React UI, Agent Growth Studio, command menu, skill-assignment overlay, backend APIs, docs, tests, and service definitions are recoverable after a server crash.

## What is included

- `frontend-react/` — React War Room UI.
  - Hamburger/command menu.
  - Panel visibility toggles.
  - Agent Growth Studio.
  - Provider/model dropdowns.
  - Per-agent skill assignment overlay.
  - Army Operations / Paperclip-style control surfaces.
- `frontend/` — older vanilla dashboard shell retained as fallback/reference.
- `backend/` — FastAPI backend APIs for roles, skills, agent growth, army operations, kanban, projects, memory, sessions, workspaces, and dashboard cache.
- `scripts/` — smoke tests and tunnel helper scripts.
- `systemd/` — service units for backend and SPA server.
- `docs/` — spec, plan, task list, tutorial, feature inventory, decisions, Excalidraw maps, and recovery memory.
- `tests/` — backend tests.
- `spa_server.py` — local SPA/proxy server that injects runtime config and proxies API/WebSocket traffic.

## What is intentionally excluded

- `state/` runtime files.
- dashboard tokens and `.env` files.
- Cloudflare tunnel logs/PIDs.
- Python virtualenvs.
- Node `node_modules`.
- local caches.

Secrets must be recreated locally through environment files, not committed.

## Current live access pattern

The intended deployment shape is:

- backend: `jarvis-dashboard.service` bound to `127.0.0.1:8502`
- SPA/proxy: `jarvis-dashboard-static.service` bound to `127.0.0.1:8503`
- public ingress: Cloudflare tunnel to the SPA/proxy

`spa_server.py` injects:

- `API_BASE=/api/plugins/jarvis-dashboard/v1`
- `WS_URL` as same-origin `/api/plugins/jarvis-dashboard/v1/ws`
- dashboard token from environment

## Restore/build

```bash
cd hermes_jarvis_war_room

python3 -m venv venv
source venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m pip install -r backend/requirements-dev.txt

cd frontend-react
npm install
npm run build
cd ..
```

Create local runtime env:

```bash
mkdir -p state
python3 - <<'PY'
from pathlib import Path
import secrets
p = Path('state/dashboard.env')
p.write_text('JARVIS_DASHBOARD_DEV_TOKEN=' + secrets.token_urlsafe(32) + '\n')
p.chmod(0o600)
PY
```

Run smoke tests after services are started:

```bash
source venv/bin/activate
set -a
. state/dashboard.env
set +a
python scripts/smoke_runtime_config.py
python scripts/smoke_premium_dashboard.py
python -m pytest tests -q
```

## Notes

This repository is a recovery snapshot of the Jarvis War Room. Dashboard-local role/model/skill overlays are intentionally profile-safe; they do not mutate Hermes profile configs unless a separate human-approved provisioning flow is run.
