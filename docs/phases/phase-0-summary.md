# Phase 0 — Read & Verify (Summary)

**Date:** 2026-06-09 02:00
**Status:** COMPLETE
**Council call:** `docs/COUNCIL_LOG.md` § 2026-06-09 02:00

## What I read

| File | LoC | What I learned |
|---|---:|---|
| `backend/api/discord_bridge.py` | 48 | Webhook receiver + in-memory `_threads_cache`. Endpoint: `POST /discord/webhook` (HMAC-signed) and `GET /discord/threads`. Needs gateway-level client. |
| `backend/api/agent_growth.py` | 520 | **Already has skill inventory + assignments + proposals**. `AgentSkillAssignment` is flat (no `project` field). `_skill_inventory()` scans `PROFILE/jarvis/skills` and `HERMES/skills`. `writes_profile_configs: false` invariant enforced. **Codex says add `project` to this model with default "default" for backward compat.** |
| `backend/jarvis_company_os/gen_agent_files.py` | 267 | SQLite-driven, hardcoded `/home/ubuntu/...` paths. Writes HEARTBEAT/TOOLS/AGENTS.md to `~/.hermes/agents/<slug>/`. **Wrong tool** — Hermes profiles are at `~/.hermes/profiles/<slug>/{config.yaml,SOUL.md}`. Build a separate script. |
| `backend/jarvis_company_os/spawn.py` | 181 | Codex subprocess worker. Env-var precedent: `JARVIS_CODEX_BINARY`, `JARVIS_WORKTREE_BASE`, `JARVIS_SPAWN_TIMEOUT`. Not directly relevant for profile creation. |
| `backend/server.py:23` | — | Imports `api.discord_bridge` as `discord_router`. **Codex says keep this stable**, add `discord_gateway.py` alongside, swap later. |
| `frontend-react/src/components/RoleMatrix.tsx:162` | — | Keys by `agent` only. Codex: keep `project="default"` default so this keeps working without changes. |
| `C:\Users\saiyu\.hermes\profiles\jarvis-boss/{config.yaml,SOUL.md}` | 2 files each | Existing format. `config.yaml` has: name, model, role, worker_kind. `SOUL.md` is plain markdown. 8 existing profiles. |

## Council call summary (codex verdict)

| # | Question | Codex's answer |
|---:|---|---|
| 1 | Profile generator | **Separate script `scripts/gen_hermes_profiles.py`**, declarative YAML, **stage → review → apply** workflow. |
| 2 | Agent Growth API | Add `project: str = "default"` to `AgentSkillAssignment`, composite identity `(project, agent)`. |
| 3 | Discord | New `backend/api/discord_gateway.py` alongside; swap import in `server.py:23` later. |
| 4 | **#1 risk** | **Path normalization**. Hardcoded `/home/ubuntu` paths in existing code. New script must use env vars only. |

## Locked plan for Phases 1-3

- **Phase 1:** `scripts/gen_hermes_profiles.py` + `state/proposals/profiles/` staging + 14 new profiles. Env-var only for paths.
- **Phase 2:** Add `project` to `AgentSkillAssignment`. Per-project skill JSON. New `SkillMarketplace.tsx` panel.
- **Phase 3:** New `backend/api/discord_gateway.py` (gateway client + thread routing + slash commands). Keep `discord_bridge.py` stable; swap import in `server.py:23` only when stable.

## Status: Phase 0 done, Phase 1 in progress.
