# Council Synthesis — Jarvis War Room Dashboard v1.1.0

**Date:** 2026-05-29  
**Council:** Boss (Claude) + Manager (Codex) + Secretary (Qwen)  
**Synthesizer:** Jarvis Manager (Codex GPT-5.5)  
**Status:** Phase 2 Build Complete. Release Gate: BLOCKED.  

---

## Executive Summary

The Jarvis War Room Dashboard is a **solid Phase 1 read-only command center with Phase 2 visual theater bolted on**. It looks impressive — Three.js constellations, CSS DNA helix, achievement toasts, WebSocket live push — but the Boss verdict is clear: **"Do not ship. Fix the foundation before hanging more curtains."**

The single most critical issue is a **1-line config bug** that causes the dashboard to report 0 agents despite 10 profiles existing on disk. Fixing this immediately brings the 3D constellation to life. Beyond that, the NL dispatch terminal (the core value proposition of a command center) is a keyword-matching stub that does not actually delegate to any agent.

---

## What EXISTS and Works

### Backend (FastAPI :8502) — 14 SOLID Features

| Feature | File | Evidence |
|---|---|---|
| Data Aggregator (30s cycle) | `core/data_aggregator.py` | Scans agents/tasks/kanban/decisions/memory/metrics/gateway |
| WebSocket Manager | `core/websocket.py` | Channel subscriptions, auto-disconnect, snapshot push |
| Rate Limiting | `server.py:62-79` | 120 req/min/IP sliding window |
| Audit Logging | `core/audit.py` + `api/audit.py` | 114 entries in `audit.jsonl` |
| Kanban Read/Write | `api/kanban.py` | Direct SQLite with WAL timeout=5.0 |
| Cache API | `api/cache.py` | 8 sub-endpoints (agents, tasks, kanban, decisions, memory, metrics) |
| Session API | `api/sessions.py` | List + transcript (falls back to state dir) |
| Discord Bridge | `api/discord_bridge.py` | Webhook receiver + thread cache |
| NL Router (keyword stub) | `api/nl_router.py` | Tier 0-3 classification via keyword matching |
| CORS | `server.py:52-58` | Locked to `127.0.0.1:8503` |
| Pydantic Models | `core/models.py` | AgentStatus, TaskBrief, KanbanCard, NLIntent, etc. |
| Auth Dependencies | `auth/dependencies.py` | Token decode + localhost bypass |
| Health Endpoint | `server.py:117-119` | Returns `{"status":"ok"}` |
| Plugin Manifest | `manifest.json` | Entry points, permissions, tab label |

### Frontend (Single HTML + JS) — 10 SOLID + 3 PARTIAL Features

| Feature | File | Status |
|---|---|---|
| Three.js 3D Agent Constellation | `js/three-constellation.js` | SOLID — starfield, glow rings, orbiting, pulsing |
| CSS 3D DNA Helix | `js/dna-helix.js` | SOLID — rotating double helix, color-coded |
| Kanban Fleet (4 columns) | `index.html:234-261` | SOLID — priority-sorted, colored borders |
| Achievement Theater | `js/theater.js` | SOLID — toast queue, confetti, XP bar, audio chime, 5 badges |
| WebSocket Client | `js/websocket-client.js` | SOLID — auto-reconnect, channel multiplexing, fallback polling |
| Session Drawer | `index.html:157-166` | SOLID — slide-up panel with search bar |
| Memory Nexus Panel | `index.html:83-93` | SOLID — pending/approved/contradiction counters |
| Decision Log Panel | `index.html:96-103` | SOLID — tier-badged cards with timestamps |
| Connection Indicator | `index.html:50-52` | SOLID — green/yellow/red dot |
| Audit Strip | `index.html:169-171` | SOLID — color-coded bottom ticker |
| Cost EKG Ribbon | `index.html:186-203` | PARTIAL — SVG renders but data is simulated (Math.random) |
| Discord Nexus Panel | `index.html:133-142` | PARTIAL — webhook receiver exists but no Discord Bot Gateway |
| Agent Heartbeat | `data_aggregator.py:67-74` | PARTIAL — only checks jarvis PID, all others marked alive unconditionally |

---

## What's BROKEN — 6 Components

| # | Component | Severity | Root Cause | Fix Effort |
|---|-----------|----------|-----------|------------|
| **B1** | **Agent scan returns 0** | CRITICAL | `config.py:7` — `PROFILE = HERMES / "profiles/jarvis"` but glob expects `HERMES / "profiles"` to find all `jarvis-*` subdirs | **1 line** (~2 min) |
| **B2** | Session drawer empty | CRITICAL | `session.db` does not exist at `~/.hermes/session.db`. No `.db` files in `~/.hermes/state/` | Needs session bridge discovery |
| **B3** | Manifest out/ dir missing | HIGH | `manifest.json:8` points to `frontend/out/index.html` which does not exist. Actual code is in `frontend/public/` | **2 lines** (~2 min) |
| **B4** | Three.js black canvas | HIGH | Cascades from B1 — `updateAgents([])` renders only starfield with zero orbs | Fix B1 resolves this |
| **B5** | Version mismatch | MEDIUM | Manifest says 1.0.0, server says 1.1.0 | 1 line |
| **B6** | WS auth bypass | MEDIUM | `websocket.py:23-27` hardcodes `"dev"` token check, doesn't use `get_current_user_ws()` | Refactor needed |

---

## What's MISSING — 12 Components

| # | Component | Priority | Why Missing |
|---|-----------|----------|-------------|
| M1 | systemd services | P0 | Not created. Backend + frontend run manually. Dies on reboot |
| M2 | Headscale VPN | P0 | Binary installed but `ip_prefixes` config rejected by v0.28.0. No Tailnet |
| M3 | Real auth (WebAuthn + TOTP + JWT) | P0 | Hardcoded `"dev"` token everywhere. No session management |
| M4 | Next.js / proper build | P1 | Still single HTML file. Manifest expects `out/` dir |
| M5 | Real NL dispatch (LLM delegation) | P1 | Keyword stub — does not call qwen3-coder or kimi-k2.6 |
| M6 | Council Chamber visualization | P1 | Placeholder text only — no 3D chamber, no voting records |
| M7 | Real session bridge | P1 | Hermes session DB location unknown. `session_search` tool works via different path |
| M8 | Server-side achievement persistence | P2 | Theater.js uses localStorage only |
| M9 | CSP headers | P2 | No Content Security Policy |
| M10 | Automated smoke tests | P2 | `scripts/smoke-test.sh` not hooked into dev workflow |
| M11 | Role segregation (operator vs viewer) | P2 | All authenticated users have full permissions |
| M12 | Real cost EKG (not simulated) | P2 | SVG uses Math.random + DOM parsing instead of aggregator cost vector |

---

## Security Concerns — 10 Findings

| # | Finding | Severity | Detail |
|---|---------|----------|--------|
| S1 | Hardcoded auth token | HIGH | `"dev"` in `websocket.py:24` and `index.html:181` |
| S2 | 127.0.0.1 bypass | HIGH | `auth/dependencies.py` auto-allows all localhost connections |
| S3 | Token in URL params | HIGH | WS auth via `?token=dev` leaks token in server logs/proxies |
| S4 | Token in HTML source | HIGH | `const TOKEN="dev"` visible in client-side JS |
| S5 | No HTTPS | HIGH | Everything is plaintext HTTP. Headscale (broken) was the transport security plan |
| S6 | No CSP headers | MEDIUM | No Content-Security-Policy on any response |
| S7 | Audit log schema mismatch | MEDIUM | API filters on `severity`/`category` but logger writes `user`/`action`/`resource` |
| S8 | No input validation on NL router | MEDIUM | `message` param passed straight to keyword matching — injection possible |
| S9 | No rate limit on WS | LOW | WebSocket endpoint not covered by HTTP rate limiting middleware |
| S10 | No dependency scanning | LOW | pip-audit / safety not run. Dependencies installed from requirements.txt unchecked |

---

## Engineering Debt — 8 Items

| ID | File | Issue |
|----|------|-------|
| D1 | `config.py:7` | PROFILE path bug — root cause of agent scan failure |
| D2 | `data_aggregator.py:13` | Wildcard import `from .config import *` |
| D3 | `server.py:25-33` | Daemon thread, no join on shutdown |
| D4 | `data_aggregator.py:218` | `LIVE_CACHE_TS` dead code |
| D5 | `websocket.py:11` | `LIVE_CACHE_META` defined but never used |
| D6 | `index.html:181` | API URL hardcoded to `127.0.0.1:8502` |
| D7 | `index.html:371-391` | Duplicate snapshot handler logic |
| D8 | All frontend | No TypeScript, no error boundaries, no loading states |

---

## Top 3 Next Priorities (Boss Verdict)

### Priority 1: FIX THE FOUNDATION (P0 — Do First)
- Fix `config.py:7` → change `PROFILE = HERMES / "profiles/jarvis"` to `PROFILE = HERMES / "profiles"`
- Fix `manifest.json` → update version to 1.1.0, point `tab` to `frontend/public/index.html`
- Verify 3D constellation populates with 10 agent orbs
- Write systemd service for backend + frontend
- This is ~30 minutes of work and makes the dashboard immediately usable

### Priority 2: REAL AUTH + VPN (P0 — Before External Access)
- Fix Headscale config for v0.28.0 schema (remove `ip_prefixes` top-level, use `prefixes:` block)
- Start Headscale, register node, verify Tailnet connectivity
- Replace `"dev"` token with JWT sessions (even if simple shared secret + expiration)
- Do NOT expose dashboard to internet until auth is real

### Priority 3: WIRE THE DISPATCH TERMINAL (P1 — Core Value)
- Replace keyword NL router with real tier gates:
  - T0: Read-only → direct cache API response
  - T1: Create task → call `hermes kanban create` via subprocess or API
  - T2: Build → delegate to `delegate_task` with Manager oversight
  - T3: Boss review → queue in council chamber, require explicit approval
- Integrate actual cost estimation from token counters
- This transforms the dashboard from "pretty monitor" into "actual command center"

---

## Council Decision

**Motion:** Proceed with Priority 1 fixes immediately (agent scan + manifest + systemd). Do NOT start Priority 2 or 3 until Priority 1 smoke tests pass.

**Votes:**
- Boss (Claude): **APPROVE** — with the condition that no further Phase 2+ features are added until P0 foundation is solid.
- Manager (Codex): **APPROVE** — estimated 30 min for P0 fixes, then full smoke test run.
- Secretary (Qwen): **APPROVE** — tasks.md must be updated after each fix to reflect actual status.

**Result:** **CARRIED UNANIMOUSLY.**

---

## Files Generated by This Council

| File | Path | Size |
|------|------|------|
| Boss Review | `/tmp/council_boss.md` | 18 KB |
| Manager Audit | `/tmp/council_manager.md` | 15 KB |
| Secretary Inventory | `/tmp/council_secretary.md` | 22 KB |
| Full Concatenated Report | `/tmp/council_full_report.md` | 55 KB |
| This Synthesis | `docs/COUNCIL_SYNTHESIS_v1.1.0.md` | — |

---

*Council chamber closed. Synthesis locked into decisions.md on release.*
