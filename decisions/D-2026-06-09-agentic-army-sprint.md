# Agentic Army Sprint — Locked decisions (2026-06-09, Saiyudh)

User approved all defaults on 2026-06-09 01:55 with **one critical override to Q1 (Discord architecture)**: the user wants a single channel `#coding_plan_feedback`, with per-project threads that auto-include the right jarvis agents. The main channel shows task-completion notifications only.

---

## Discord architecture (revised per user instruction)

**User's words (2026-06-09 01:55):**
> "for jarvis and army i have one channel, the channel is called coding_plan_feedback, I want to be able to talk to any bot and also the bots can discuss within themselves. whenever I start a discussion on a project it should open a new thread and all the jarvis agents i can access through that and in the main channel coding_plan_feedback it will give me notifications if tasks were completed."

**Implications:**

- **One Discord channel:** `#coding_plan_feedback` (the user already has this set up).
- **Per-project thread auto-created** when the user starts a new discussion (e.g. "design a new login page" → thread `#thread-login-page`).
- **All 22 jarvis profiles are reachable in any thread.** The user can `@jarvis-frontend` or `@jarvis-ui_ux` etc. inside a thread.
- **Bots can talk to each other** within a thread (e.g. jarvis-frontend asks jarvis-ui_ux for a design review; both speak in the same thread).
- **The main channel (`#coding_plan_feedback`) is notification-only** — bot posts short task-completion notifications (e.g. "✅ jarvis-qa-lead: smoke tests passed for project=war-room phase 2").
- **Slash commands** (still useful): `/ask <profile> <prompt>` opens a thread, `/threads list` shows open threads, `/thread close` archives.

**Trade-off vs original "1 channel per profile" plan:**
- ✅ Single channel = single bot token (clean, easy to audit).
- ✅ Threads keep conversation scoped per project.
- ✅ User can route to any agent in any thread.
- ⚠️ Thread title vs profile name disambiguation needed (user types `@jarvis-frontend help` inside a thread).
- ⚠️ The bridge must track thread→project→active-agents mapping.

**Implementation note for Phase 3:** the bridge reads messages from `#coding_plan_feedback`, detects thread-create events, and (per slash command or `@mention`) routes to the right profile. The thread itself is the conversation scope; the main channel is the notification feed.

---

## Q1–Q8 final answers

| # | Question | User's choice |
|---:|---|---|
| 1 | Discord architecture | **1 channel `#coding_plan_feedback` + per-project threads** (custom) |
| 2 | Skill import scope | **Tier-1 + T2 (default)** — 7 repos, 2,500+ skills |
| 3 | Profile creation order | **All 14 in Phase 1** (user: "All 14") |
| 4 | Department count | **Keep all 13 separate** (user: "I want to keep it separate as I will be feeding a lot of skills and mcp for one agent it might become too bloated and blow up context windows") |
| 5 | Council of Departments | **Yes, build it in Phase 4** — keep existing 3-stage council too |
| 6 | Channel names | **`#jarvis-<profile>`** for profile identity inside threads; main channel is `#coding_plan_feedback` |
| 7 | Council chair model | **Codex for now**; **multi-model pluggable later** (user: "for now as codex is my main thing, keep the council as codex for now but later I want to add more models to it. So that I can add local models too if i want to inside it") |
| 8 | Skill selection UI | **New `SkillMarketplace.tsx` panel** (user: "You can make a new panel") |

**Process rule from user (2026-06-09 01:55):**
> "before the start of each phase and within major tasks and also end of phase updates call council with codex. so that everything is going according to plan."

→ **Council call at:** start of each phase, before each major task (e.g. before each of the 14 profile creations in Phase 1), and at end of each phase. Code log at `docs/COUNCIL_LOG.md`.

**Memory rule from user (2026-06-09 01:55):**
> "Complete all phases maintain ledger or memory somehow so that you and codex don't get lost."

→ **Running ledger at `docs/COUNCIL_LOG.md`** + a per-phase summary file in `docs/phases/` + a `_research/` session log.

**Goal (2026-06-09 01:55):**
> "/goal complete all the phases"

→ All 6 phases (Phase 0 read, Phase 1 profiles, Phase 2 catalog, Phase 3 Discord, Phase 4 Council of Departments, Phase 5 hardening) shipped end-to-end.

---

## Plan (locked, 2026-06-09 01:55)

| Phase | Scope | Estimated time |
|---|---|---|
| 0 | Read & verify the 5 critical backend modules + Hermes docs + the Discord skill repos | 2-3h |
| 1 | Profile generator v2 — all 14 new profiles at once (so_uled: ui_ux, frontend, backend, mobile, data-ml, devops, marketing, sales, finance, legal, customer-success, plus rename researcher→jarvis-researcher, plus add the 2 missing ones) | 4-6h |
| 2 | Skill catalog + dashboard panel + 4 trust tiers + Tier-1/T2 import | 6-8h |
| 3 | Discord bridge v2 — single channel `#coding_plan_feedback` + per-project threads + slash commands | 8-10h (slightly more due to custom arch) |
| 4 | Council of Departments v1 + multi-model pluggable council (chair is codex, but config supports local models) | 6-8h |
| 5 | Production hardening | 4-6h |

**Total: 30-41 hours.** I will run end-to-end in this session, with council calls (codex) before each phase + before each major task + at end of each phase, as you requested.

**Status:** Phase 0 starting now.

## Context

The user (Saiyudh) asked on 2026-06-09:

> "Find github repos like alirezarezvani/claude-skills from the internet, do deep research on them, and help me create hermes profiles so that I can then connect each profile to a discord bot. And then have conversations form there if needed. But first is research on how to improve and create an agentic army... find repos which have good division of departments and teams, then for each department carry out intensive research with what skills can be fed to that specific agent... create hermes profiles for each specialized agents which I can grow... In my dashboard I want to update this system too where it will only show skill which each respective agent has and that I can select which ones to use for a certain project or not and keep that decision saved and used through out the project... set this as goal to do don't stop until you finish."

This decision brief captures the **proposed plan** synthesized from the research sprint. It is **not** an implementation commit; it is a request for approval.

## What we already have (re-used, not duplicated)

Per `docs/RESEARCH_FINDINGS.md` (2026-06-08 master) and the current project state:

- **Engine:** existing FastAPI + WebSocket + SQLite stack (Decision 2026-06-08)
- **Observability:** Langfuse (default) + OpenTelemetry
- **Editor:** xyflow (2D) + R3F (3D)
- **Memory:** 3-tier — Hindsight + mem0 + Graphiti + Chroma + FalkorDB (`docs/MEMORY_STRATEGY.md`)
- **Council:** karpathy 3-stage (`jarvis-council`)
- **Management protocol:** decision rights + handoff schemas + escalation (`docs/MANAGEMENT_PROTOCOL.md`)
- **Departments (6 existing):** engineering, research, marketing, finance-ops, product, security (`docs/departments/`)
- **Profiles (8 existing):** jarvis-boss, jarvis-manager, jarvis-secretary, jarvis-engineering-lead, jarvis-qa-lead, jarvis-security-lead, jarvis-docs-lead, jarvis-product-lead, jarvis-scout, jarvis-council (in `C:\Users\saiyu\.hermes\profiles\`)
- **Agent Growth Studio:** `backend/api/agent_growth.py` (assignments + proposals)
- **Discord bridge:** `backend/api/discord_bridge.py` (49 lines, minimal)
- **Reference repos cloned:** MiroFish-Offline, llm-council, AI-CoScientist, claude-skills

## What's new (the proposed additions)

### 1. 14 new Hermes profiles
**Total post-sprint: 22 profiles** (8 existing + 14 new). New: jarvis-frontend, jarvis-ui_ux, jarvis-backend, jarvis-mobile, jarvis-data-ml, jarvis-devops, jarvis-marketing, jarvis-sales, jarvis-finance, jarvis-legal, jarvis-customer-success, plus rename `researcher` → `jarvis-researcher`. 13-department taxonomy (adds ui-ux, frontend, backend, mobile, data-ml, devops, sales, legal, customer-success to the existing 6).

### 2. Skill catalog system
- New `state/skill_catalog/` JSON store with provenance, trust-tier, signature_required flags
- 4 trust tiers (T0 local / T1 curated / T2 bulk / T3 untrusted) with security guardrails (prompt-injection quarantine)
- Default import: 4 curated repos (`alirezarezvani/claude-skills`, `mxyhi/ok-skills`, `bergside/awesome-design-skills`, `mukul975/Anthropic-Cybersecurity-Skills`) + 3 bulk indexes (`sickn33/antigravity-awesome-skills`, `ComposioHQ/awesome-claude-skills`, `VoltAgent/awesome-agent-skills`) — about 2,500+ skills discoverable, ~50 active per agent per project

### 3. Discord bot wiring
- **Recommendation: one bot, one channel per agent** (not one bot per agent)
- Channel name: `#jarvis-<profile>` (default)
- Per-channel config in `state/discord_guild.json`
- Slash commands: `/ask <profile> <prompt>`, `/skills <profile>`, `/add-skill`, `/remove-skill`
- Thread-per-conversation; conversation history persists in the bot's channel
- Bridge extends existing `backend/api/discord_bridge.py`

### 4. Dashboard skill-selection UI
- New `frontend-react/src/components/SkillMarketplace.tsx` panel
- 3-column layout: active / available / dormant, per-project per-agent
- Backend endpoints added to `backend/api/agent_growth.py`:
  - `GET /agents/<name>/skills?project=X`
  - `POST /agents/<name>/skills`
  - `GET /skills/catalog?dept=UI`
  - `POST /skills/import-from-repo`

### 5. Council of Departments (Phase 4)
- New `jarvis-council-departments` profile (router-only)
- Picks 1-3 relevant departments per query
- Synthesizes responses using the existing 3-stage council pattern

### 6. Phased build plan (5 phases, 26-37 hours)

| Phase | Scope | Testable? |
|---|---|---|
| 0 | Read & verify the 5 critical backend modules + Hermes docs | Written report |
| 1 | Profile generator v2 (3 profiles first: frontend, ui_ux, backend) | pytest |
| 2 | Skill catalog + SkillMarketplace.tsx panel | pytest + vitest |
| 3 | Discord bot bridge v2 + slash commands | pytest + manual Discord |
| 4 | Council of Departments v1 | pytest |
| 5 | Production hardening | smoke tests |

## Options considered

### A. Do this sprint (recommended)
- 22 profiles, ~2,500 skills indexed, 1 Discord bot, 1 dashboard panel, Council of Departments
- 26-37 hours of build time, 1-2 weeks part-time
- Cost: $0/month net-new (within user's existing $20 ChatGPT plan)
- 8 open questions for the user to answer before Phase 0 starts

### B. Smaller scope — just profiles + Discord
- Skip skill catalog and dashboard panel
- 14 new profiles + Discord bridge v2
- ~14 hours of build time
- Loses the user's "feed agents good github repos as food" vision

### C. Smaller scope — just skill catalog
- Skip the 14 new profiles; rely on existing 8
- Build skill catalog + dashboard panel + import scripts
- ~14 hours
- Doesn't address "create hermes profiles for each specialized agent"

### D. Defer
- Document the plan but don't build yet
- 0 hours
- Risks losing the user's momentum

**Recommendation: Option A**, in 5 phases with explicit approval gates between phases.

## Cost analysis

| Item | Cost | Notes |
|---|---|---|
| 22 profiles | $0 | Generated by script (extends `gen_agent_files.py`) |
| Skill catalog | $0 | `git clone` + parse SKILL.md |
| 1 Discord bot | $0 | Free tier |
| Codex usage (for code review + council chair) | $0 (inside $20 plan) | Within ChatGPT subscription |
| Local Ollama (for cheap tasks) | $0 | Disk only; 8GB VRAM fits a 7B Q4 |
| New MCP servers (playwright, git, postgres) | $0 | All free |
| **Net new monthly cost** | **$0** | Already-paid ChatGPT sub |

## Risk analysis

| Risk | Mitigation |
|---|---|
| Codex usage spikes when 22 agents are active | Route cheap tasks to local Ollama; reserve codex for code review + council chair |
| Bulk skill import brings prompt-injection | Quarantine folder; trust tier signature_required; daily sync |
| 22 profiles may bloat the dashboard's data load | Per-agent skill activation is a dashboard-local overlay (per Decision 7) |
| Discord rate limits hit during heavy use | Per-channel rate limit + backoff in the bridge |
| Hermes profile isolation may not be as strong as assumed | Phase 0 reads the docs end-to-end; profile isolation test in Phase 1 |
| Council of Departments may pick wrong departments | Phase 4 ships with a smoke test + human override always available |

## Hard rules (carried from existing project)

- **Decision 7 (D-2026-06-01):** Dynamic role/model mapping stays dashboard-local; never mutate Hermes profile configs without explicit human approval
- **Decision 8 (D-2026-06-03):** Army Operations is additive, dashboard-local, Claude-first until codex exists (now superseded by codex availability)
- **CLAUDE.md:** RED → GREEN → REFACTOR. Failing test first, then implement.
- **User Challenge rule:** Boss+Manager cannot override Saiyudh on a User Challenge, even with unanimous agreement

## 8 open questions for the user

(These are the only things blocking the start of Phase 0. The full text is in `docs/RESEARCH_LEDGER_AGENTIC_ARMY.md`.)

1. **Discord bot pattern:** one bot / channel per agent (default), one bot per agent, or slash-command-only?
2. **Skill import scope:** Tier-1+T2 (default, ~2,500 skills), Tier-1 only, or all tiers?
3. **Profile creation order:** frontend+ui_ux+backend first (default), all 14 in one shot, or user-named?
4. **Department count:** keep all 13 (default), merge ui-ux+frontend, or merge sales+marketing?
5. **Council of Departments:** build it (default) or skip?
6. **Discord channel names:** `#jarvis-<profile>` (default) or human-friendly?
7. **Council chair model:** codex (default), local Ollama, or hybrid?
8. **Skill selection UI:** new SkillMarketplace.tsx panel (default), reuse AgentConstellation tab, or modal?

## Recommendation

**Proceed with Option A (5-phase plan) once the 8 open questions are answered.**

Phase 0 (read & verify) starts the moment questions are answered. Each phase is independently shippable and testable. Rollback is `git revert` per phase. The user maintains approval at every phase boundary (we pause and report between phases).

## Next step

Wait for Saiyudh's answers to the 8 open questions. Once received, dispatch the Phase 0 plan as a Decision Brief and start.

---

**Approval needed from:** Saiyudh (User Challenge: which scope of the 22-profile vision to build).
**Council verdict:** not yet convened (pending user input).
**Pre-emit verification:** this brief was reviewed by codex (gpt-5.5) for weak claims and missing pieces; all 10 findings are addressed in § Post-sprint corrections of the research ledger.
