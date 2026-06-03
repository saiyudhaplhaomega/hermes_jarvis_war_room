# Jarvis War Room Project Memory

This file is project-local memory for future agents working on Hermes War Room.

## Non-negotiable setup rule

Saiyudh's War Room is project-wise.

- The selected project is the working context.
- Agent setup and adding new agents are project-specific by default.
- Role/model assignments, agent skill feeding, tasks, runs, workspaces, docs, and memory updates must attach to the active project unless Saiyudh explicitly says they are company/global.
- The dashboard can show global/company-wide summaries, but write actions must default to the active project.
- Never silently add agents to a global/default pool.
- If the active project is unclear before a mutation, ask or infer safely from the project selector/workspace state.

## Scope guardrail

This repository is Hermes War Room:
`/home/ubuntu/.hermes/profiles/jarvis/plugins/jarvis-dashboard`

Do not use Skin Lesion/XAI instructions, docs, prompts, or frontend context for War Room work.

## Required files to read before edits

1. `docs/FEATURE_INVENTORY.md`
2. `docs/PROJECT_MEMORY.md`
3. `docs/decisions.md`
4. `docs/spec.md`, `docs/plan.md`, `docs/tasks.md` when changing architecture or behavior

## Recovery note from 2026-06-03

MiniMax partially migrated the live HTML chat panel from `chat-history` to `chat-thread` and left stale JavaScript references. Future agents must preserve DOM/JS contracts and update the inventory after any UI change.

## Recovery record — 2026-06-03T18:48:05+08:00

Fixed War Room live dashboard after crash/MiniMax damage:

- Restored live static service to `spa_server.py`; plain `python -m http.server` is forbidden because it breaks `/war-room`, runtime config injection, and API proxying.
- Locked backend to `127.0.0.1:8502` and static SPA to `127.0.0.1:8503`; Cloudflare tunnel remains the public path.
- Added private shared service env file at `state/dashboard.env` with mode `600`; do not print or commit its token.
- Repaired frontend runtime config to use `window.__CONFIG__`, same-origin `/api/plugins/jarvis-dashboard/v1`, and injected token rather than hardcoded public backend IP or `dev` token.
- Repaired chat DOM contract: `chat-thread` is the live element; `chat-history`, `cmd-input`, and `cmd-send` must not reappear.
- Repaired voice input target to use `nl-input` and `sendChat()`.
- Deduplicated workspace functions and workspace polling.
- Preserved project-wise behavior: active project selector drives context; agent setup/add-agent defaults to active project only.
- Added Three.js graceful fallback and CSP allowlist for the existing Tailwind/CDNJS/font origins so the visual constellation can render when network allows.
- Updated smoke tests to protect against hardcoded backend IP/dev token regressions.

Verified:

- `python scripts/smoke_runtime_config.py` PASS.
- `python scripts/smoke_premium_dashboard.py` PASS.
- `python -m pytest tests -q` -> `16 passed`.
- Dev test dependencies are recorded in `backend/requirements-dev.txt` (`pytest`, `httpx2`).
- Local `/war-room` -> HTTP 200.
- Local API proxy `/dashboard/cache` -> HTTP 200.
- Cloudflare `/war-room` -> HTTP 200.
- Public browser API checks `/dashboard/cache`, `/project/list`, `/workspace/list` -> 200/200/200.
- Public browser console after clear -> 0 messages, 0 JS errors.
