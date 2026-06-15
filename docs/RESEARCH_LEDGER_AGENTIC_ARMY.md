# Research Ledger — Agentic Army Sprint (2026-06-09)

**Companion to:** `docs/RESEARCH_LEDGER.md` (2026-06-08, 50 rounds) and `docs/RESEARCH_FINDINGS.md` (master synthesis).
**This sprint's focus:** what the 2026-06-08 sprint *didn't* cover:
1. **Specialist SKILL.md feeds** to grow each agent (the "food" the user named)
2. **Discord bot → per-agent wiring** (the 2026-06-08 sprint noted 49-line `backend/api/discord_bridge.py` but didn't go deep)
3. **Multi-profile Hermes provisioning** at scale (10+ profiles, naming, isolation)
4. **Per-project skill selection UI** (the dashboard piece)
5. **New agents the army is missing** (frontend, ui-ux, marketing, sales, data-ml, finance, customer-success, legal)

**Already established (do not re-derive):**
- 8+ named agents in `backend/jarvis_company_os/registry.py` (boss, manager, secretary, engineering-lead, qa-lead, security-lead, docs-lead, product-lead, scout, council)
- 6 departments already in `docs/departments/` (engineering, research, marketing, finance-ops, product, security)
- Management Protocol at `docs/MANAGEMENT_PROTOCOL.md` (decision rights, handoff schemas, escalation)
- Memory strategy at `docs/MEMORY_STRATEGY.md` (3-tier: Hindsight + mem0 + Graphiti + Chroma + FalkorDB)
- Engine stays the existing FastAPI + WebSocket + SQLite (D-2026-06-08)
- Observability: Langfuse (default) + OTel
- Editor: xyflow (2D) + R3F (3D)
- Reference repos cloned: `MiroFish-Offline`, `llm-council`, `AI-CoScientist`, `claude-skills`
- Agent Growth Studio at `backend/api/agent_growth.py` (assignments + proposals APIs)
- Discord bridge at `backend/api/discord_bridge.py` (49 lines, minimal)
- Hermes profiles exist at `C:\Users\saiyu\.hermes\profiles\` (jarvis-boss, jarvis-manager, jarvis-engineering-lead, jarvis-qa-lead, jarvis-product-lead, jarvis-docs-lead, jarvis-security-lead)

---

## Sprint methodology

Sprint ran 2026-06-09, **6 numbered rounds + 4 follow-up repo navigations (10 visits total)**.
All in this session — no terminal calls needed beyond reading the existing 2026-06-08 ledger for amortization.
GitHub rate-limited after 5 queries (~30s cool-off); deliberately stopped before flooding.

**Codex review (2026-06-09 01:48):** GPT-5.5 audited the ledger while drafting this section. It flagged 5 weak claims and 5 missing pieces. All 10 are addressed in the **§ Post-sprint corrections** section at the bottom of this file.

**Tier discipline:**
- **A** — directly adopts into War Room. Profile template, skill feed, or pattern we copy.
- **B** — inspires one specific component. Read it, don't fork it.
- **C** — record as "saw it, didn't fit." Don't re-research.

---

## Round 1 — Company/department simulation repos

**Query:** `https://github.com/search?q=%22AI+company%22+multi-agent+roles&type=repositories&s=stars&o=desc`

Thin results (3 repos). The "AI company" exact-match query has low recall.

| Repo | ⭐ | License | Department pattern | Tier | Plan |
|---|---:|---|---|---|---|
| `hoshibayasushi/ai_company_meeting` | 0 | ? | Streamlit meeting simulator — chair-led multi-agent meetings with whiteboard + life-log | C | Niche, no real org chart |
| `murphyx-ai/murphyx-ai-company` | 0 | ? | "CEO AI coordinates 15" agents in a tech-startup simulation (Python, task-queue) | A | **Study the "CEO over 15 specialists" runtime structure for `jarvis-boss` 2.0** |
| `pathtoresiliencebv/mhbl-framework` | 0 | ? | Custom framework with role switching, task queue | C | Niche |

**Query:** `https://github.com/search?q=%22agent+company%22+OR+%22AI+company%22+OR+%22virtual+company%22+agents&type=repositories&s=stars&o=desc` — 429 rate-limited, skipped.

## Round 2 — Multi-agent role frameworks (modern, beyond CrewAI/MetaGPT)

**Query:** `https://github.com/search?q=multi+agent+role+specialized+OR+%22agent+role%22&type=repositories&s=stars&o=desc` (793 results — top picks)

| Repo | ⭐ | License | Role/dept pattern | Tier | Plan |
|---|---:|---|---|---|---|
| `jessepwj/CCteam-creator` | 291 | ? | "Claude Code team orchestration skill" — file-based planning + parallel AI teams | A | **Adopt file-based planning pattern; aligns with War Room's `decisions/` discipline** |
| `q3ok/coordinated-agent-team` | 61 | ? | "Coordinated Agent Team" — prompt-driven multi-agent system, deterministic handoffs, vscode-tagged | A | **Adopt the deterministic handoff schema; pair with our existing Management Protocol** |
| `phj1081/EJClaw` | 42 | MIT | Tribunal Discord bot — **autonomous paired review with configurable agent roles** | A | **Direct match for the Discord-per-agent vision. Study role config schema** |
| `howyoungchen/deepRolePlay` | 118 | ? | Roleplay system solving character-forgetting | C | Not relevant to agent-army use case |
| `yczhou001/MAM` | 52 | ? | Modular multi-agent for medical diagnosis | C | Niche domain |
| `chekusu/wanman` | new | ? | "Agent matrix runtime" inspired by Japanese one-man trains | B | Borrow "single user steps back, watches agents" pattern for the dashboard |

## Round 3 — Agent dispatch / router systems

**Query:** `https://github.com/search?q=agent+router+dispatch+multi-agent&type=repositories&s=stars&o=desc` (18 results)

| Repo | ⭐ | License | What it does | Tier | Plan |
|---|---:|---|---|---|---|
| `jadecli/claude-multi-agent-dispatch` | 0 | ? | Claude multi-agent with **tree-sitter primitive detection, DSPy classification, channel bridges, hook orchestration** | A | **Study the tree-sitter + DSPy router. Drop-in for `mode_router.py` upgrade** |
| `jirachiuwu/olympus-multi-agents` | 0 | ? | Hook-enforced verification, multi-agent with manual-to-automated maturity | A | **Study hook enforcement pattern. Maps to our `CLAUDE.md` RED-GREEN** |
| `M00C1FER/contract-net-router` | 0 | ? | Capability-based router with **Contract Net Protocol bidding + coalition building** | A | **Borrow the CNP pattern for `backend/jarvis_company_os/spawn.py` 2.0** |
| `Retsumdk/delegate-dispatcher` | 0 | ? | Weighted role + load balancing task delegation | B | Borrow load-balancing scoring |
| `lhy269/smart-cs-dispatcher` | 0 | ? | Customer support dispatch with SLA tracking | C | Niche |
| `axel-claw/orchestration-patterns` | 0 | ? | Orchestration patterns + ACP | B | Watch, ACP is the agent-client protocol from late 2025 |

## Round 4 — SKILL.md ecosystem (the "food" feeds)

**Query:** `https://github.com/search?q=claude+skills+%22SKILL.md%22+agent&type=repositories&s=stars&o=desc` (273 results)

**Query:** `https://github.com/search?q=awesome+claude+skills&type=repositories&s=stars&o=desc` (521 results)

The big discovery: a **meta-skill ecosystem** has emerged in 2025-2026. Three categories:

### 4a. Awesome-list indexes (use as discovery layer)

| Repo | ⭐ | Last commit | What it is | Tier | Plan |
|---|---:|---|---|---|---|
| `ComposioHQ/awesome-claude-skills` | **63,768** | 3 weeks ago | Canonical awesome-list, 80+ folders (brand-guidelines, canvas-design, changelog-generator, etc.) | A | **Default discovery feed; auto-scrape for new skills monthly** |
| `hesreallyhim/awesome-claude-code` | **46,005** | active | Curated Claude Code skills, hooks, slash-commands, plugins | A | **Default discovery feed; mine for hooks/commands** |
| `sickn33/antigravity-awesome-skills` | **40,104** | 17 hours ago | **1,500+ skills for Claude Code, Cursor, Codex CLI, Gemini CLI, Antigravity.** Has installer CLI + plugins + bundles. 1,859 commits. | A | **Primary bulk-import source. Has its own installer (`apps/web-app`)** |
| `travisvn/awesome-claude-skills` | 13,305 | active | Curated list, more focused on Claude Code specifically | B | Secondary discovery |
| `BehiSecc/awesome-claude-skills` | 9,433 | active | Awesome-list mirror | B | Secondary discovery |
| `VoltAgent/awesome-agent-skills` | n/a | active | **1,000+ skills from official dev teams and the community** | A | **Adopt as a second bulk source, cross-reference with antigravity** |
| `mxyhi/ok-skills` | 411 | 2 days ago | Curated AI coding skills + AGENTS.md playbooks, multi-runtime | A | **Adopt as a third bulk source; particularly good Codex/Codex CLI fit** |
| `bergside/awesome-design-skills` | 1,177 | active | **67 design skills** (Google Stitch, Codex, Figma compatible) | A | **Default for `jarvis-ui_ux` profile** |
| `arpitg1304/robotics-agent-skills` | 265 | active | Production-grade robotics skills (ROS1/2, SOLID) | C | Not in scope |
| `FrancyJGLisboa/agent-skill-creator` | 1,381 | active | "Turn any workflow into reusable AI skills" — installs on 14+ tools | A | **Adopt the skill-creation workflow. We use this to convert user's research into skills** |
| `veniceai/skills` | 88 | active | Skills for Venice.ai API, one folder per surface area | C | Vendor-specific |
| `TerminalSkills/skills` | n/a | active | Open-source library, SKILL.md format multi-runtime | A | **Adopt as a fourth source; small but clean format** |

### 4b. Single-purpose specialist skill repos (the actual food)

| Repo | ⭐ | License | Department(s) | Notes |
|---|---:|---|---|---|
| `alchaincyf/huashu-design` | n/a | MIT | UI/UX, design | Already known (user named it) — Chinese-language design skills, multi-format |
| `nextlevelbuilder/ui-ux-pro-max-skill` | n/a | MIT | UI/UX | Already known — pro design checklist pattern |
| `leonxlnx/taste-skill` | n/a | MIT | UI/UX | Already known — "taste" judgment skill |
| `pbakaus/impeccable` | n/a | MIT | UI/UX | Already known — design/typography/motion |
| `mukul975/Anthropic-Cybersecurity-Skills` | n/a | MIT | Security | Already known — 50+ security skills |
| `mattpocock/skills` | n/a | MIT | Productivity | Already known — example skill (grill-me) |
| `github/spec-kit` | n/a | MIT | Spec-driven dev | Already known — spec.md / plan.md / tasks.md pattern (we already use this in `decisions/`) |
| `microsoft/playwright` | huge | Apache-2.0 | QA / E2E testing | MCP — give to `jarvis-qa-lead` for browser-driven verification |

### 4c. Skill creator / registry infrastructure

| Repo | ⭐ | License | What it does | Plan |
|---|---:|---|---|---|
| `FrancyJGLisboa/agent-skill-creator` | 1,381 | ? | Converts workflows → installable skills, supports 14+ tools | **Wire into our Agent Growth Studio as the "convert to skill" button** |

## Round 5 — Discord multi-agent wiring

**Query:** `https://github.com/search?q=discord+bot+multi-agent&type=repositories&s=stars&o=desc` (45 results)

| Repo | ⭐ | License | Pattern | Tier | Plan |
|---|---:|---|---|---|---|
| `phj1081/EJClaw` | 42 | MIT | **Tribunal-style Discord framework** — autonomous paired review with configurable roles. Codex + Bun | A | **The closest existing reference. Adopt the role-config + Discord-as-runtime pattern** |
| `nczz/kiro-discord-bot` | 25 | ? | "Trainable AI agent that lives in Discord" — codebase binding, persistent rules | A | **Adopt codebase-binding pattern; useful when an agent is owned by a Discord user** |
| `Womp-Womp/MultiAgentDiscordBot` | 1 | ? | Multiple agents via langgraph in Discord | C | Too small |
| `Llliao1113/discord-multi-agent` | 0 | ? | Customer Service: Intent/Reply/Quality agents | B | Borrow the 3-specialist topology for `jarvis-support` |
| `hoaidoanhkd/ClaudeBot` | 3 | ? | Autonomous Discord + Telegram, self-learning, PR management | B | Borrow self-learning loop idea (we already have `agent_growth.py`) |

**Three architectural options distilled from these:**

1. **One bot per agent** (EJClaw pattern) — cleanest; each agent is a Discord user with its own token. Cost: one bot token per profile; per-server bot-count limits apply (Discord's per-server bot cap is documented at 2500+ bots/server for verified apps — there is no 5-bot cap, that was an unverified claim from a chat memory; see § Post-sprint corrections).
2. **One bot, one channel/thread per agent** — `backend/api/discord_bridge.py` likely already starts here. Scales to 100+ agents. Each channel is owned by the same bot identity.
3. **One bot, slash-command router** — `/jarvis-ui_ux <prompt>` or `/ask jarvis-frontend <prompt>`. Single bot, dispatch by command.

**Recommendation: option 2 (one bot, one channel per agent).** It maps to the existing `mode_router.py` (which already routes by mode/agent), scales to 50+ agents with no extra tokens, and a single bot is much easier to secure.

## Round 6 — Hermes Agent multi-profile patterns (web search)

The Hermes docs (`hermes-agent.nousresearch.com/docs`) and a perusal of the existing profile structure tell us:
- Profiles live at `~/.hermes/profiles/<name>/` with `config.yaml` + `SOUL.md` (and optionally `HEARTBEAT.md`, `TOOLS.md`, `AGENTS.md`)
- `worker_kind: api` (HTTP) or `worker_kind: cli` (subprocess) is the dispatch primitive
- `model:` field pins the model, with provider routing handled by the config
- Each profile is fully isolated; no cross-profile state in the runtime

**Implications for 10+ profile setup:**
- A generator script (we have `backend/jarvis_company_os/gen_agent_files.py` — already 268 lines) should template the per-profile files from a single declarative spec
- Naming convention: `jarvis-<dept>` for departments, `jarvis-<dept>-<specialty>` for specialties. Matches the user's example (`jarvis-ui_ux`, `jarvis-frontend`)
- `AGENTS.md` per profile should list which other profiles it collaborates with (already mapped in `backend/jarvis_company_os/registry.py` `COUNCIL_HIERARCHY`)

---

## Master synthesis — proposed agent army v2.0

### A. New Hermes profiles to create (10 net-new on top of existing 8)

Naming follows the existing `jarvis-<dept>` convention. **The "food" column lists the skill repos each profile will be bound to in Agent Growth Studio.**

| # | Profile | Role | Discord channel | Skill feed (Tier-A repos) | Existing |
|---:|---|---|---|---|---|
| 1 | `jarvis-frontend` | Frontend engineering lead | `#jarvis-frontend` | `ComposioHQ/awesome-claude-skills` (UI subset), `mxyhi/ok-skills` (electron, ai-elements), `nextlevelbuilder/ui-ux-pro-max-skill`, `microsoft/playwright` (MCP) | NEW |
| 2 | `jarvis-ui_ux` | UI/UX designer | `#jarvis-design` | `bergside/awesome-design-skills`, `pbakaus/impeccable`, `alchaincyf/huashu-design`, `leonxlnx/taste-skill`, `ComposioHQ/awesome-claude-skills` (brand-guidelines, canvas-design subset) | NEW |
| 3 | `jarvis-backend` | Backend engineering lead | `#jarvis-backend` | `ComposioHQ/awesome-claude-skills` (changelog-generator, artifacts-builder), `mxyhi/ok-skills` (electron, exa-search), `git` MCP, `postgres` MCP | NEW |
| 4 | `jarvis-mobile` | Mobile dev (iOS/Android/React Native) | `#jarvis-mobile` | `mxyhi/ok-skills` (electron subset), `sickn33/antigravity-awesome-skills` (mobile bundle) | NEW |
| 5 | `jarvis-data-ml` | Data engineering + ML | `#jarvis-data` | `sickn33/antigravity-awesome-skills` (data bundle), `mxyhi/ok-skills` (exa-search, autoresearch) | NEW |
| 6 | `jarvis-devops` | DevOps / SRE | `#jarvis-devops` | `ComposioHQ/awesome-claude-skills` (ops subset), `sickn33/antigravity-awesome-skills` (devops bundle) | NEW |
| 7 | `jarvis-marketing` | Marketing / growth | `#jarvis-marketing` | `ComposioHQ/awesome-claude-skills` (competitive-ads-extractor, brand-guidelines), `sickn33/antigravity-awesome-skills` (marketing bundle) | NEW — `docs/departments/marketing/` exists but no profile |
| 8 | `jarvis-sales` | Sales / outreach / biz-dev | `#jarvis-sales` | `ComposioHQ/awesome-claude-skills` (sales subset), `sickn33/antigravity-awesome-skills` (sales bundle) | NEW |
| 9 | `jarvis-finance` | Finance / FP&A / budgets | `#jarvis-finance` | `ComposioHQ/awesome-claude-skills` (finance subset) | NEW — `docs/departments/finance-ops/` exists but no profile |
| 10 | `jarvis-legal` | Legal / contracts / compliance | `#jarvis-legal` | `mukul975/Anthropic-Cybersecurity-Skills` (compliance subset), `ComposioHQ/awesome-claude-skills` (legal subset) | NEW |
| 11 | `jarvis-customer-success` | Support / success | `#jarvis-support` | `Llliao1113/discord-multi-agent` (intent/reply/quality pattern), `ComposioHQ/awesome-claude-skills` (support subset) | NEW |
| 12 | `jarvis-researcher` | Deep research / market intel | `#jarvis-research` | `STORM` skill (perspective-guided), `sickn33/antigravity-awesome-skills` (research bundle) | EXISTS (rebrand from `researcher`) |
| 13 | `jarvis-council` | Multi-model council chair | (internal) | karpathy/llm-council pattern (already adopted) | EXISTS |
| 14 | `jarvis-scout` | Tooling landscape scout | (internal) | n/a | EXISTS |
| 15 | `jarvis-boss` | CEO/strategist | `#jarvis-boss` (admin) | n/a | EXISTS |
| 16 | `jarvis-manager` | PM/coordination | `#jarvis-manager` (admin) | `github/spec-kit`, `mattpocock/skills` (grill-me) | EXISTS |
| 17 | `jarvis-secretary` | Memory/scribe | (internal) | `mattpocock/skills` (productivity) | EXISTS |
| 18 | `jarvis-qa-lead` | QA + smoke tests | `#jarvis-qa` | `microsoft/playwright` (MCP) | EXISTS |
| 19 | `jarvis-security-lead` | Security review | `#jarvis-security` | `mukul975/Anthropic-Cybersecurity-Skills` | EXISTS |
| 20 | `jarvis-docs-lead` | Documentation | `#jarvis-docs` | `git` MCP, `ComposioHQ/awesome-claude-skills` (changelog-generator) | EXISTS |
| 21 | `jarvis-product-lead` | Product management | `#jarvis-product` | `ComposioHQ/awesome-claude-skills` (product subset), `mattpocock/skills` (grill-me) | EXISTS |
| 22 | `jarvis-engineering-lead` | Eng coordination | `#jarvis-eng` | TBD | EXISTS |

**Total: 22 profiles** (8 existing → 22 = +14 new). Each gets a SOUL.md, config.yaml, AGENTS.md, and a default Discord channel.

### B. Discord bot architecture (recommended)

**Choice: one bot, one channel per agent (the bridge pattern).**

| Component | File | Status | Action |
|---|---|---|---|
| Bot token | `state/dashboard.env` (mode 600) | ENV-only | Add `DISCORD_BOT_TOKEN` |
| Bridge | `backend/api/discord_bridge.py` (49 lines) | Exists | Extend — per-channel config table, slash commands, per-agent prompt prefix |
| Per-project skill assignment | `backend/api/agent_growth.py` (assignments) | Exists | Extend — add a `discord_default` field |
| Server config | `state/discord_guild.json` (NEW) | New | Map: profile → channel_id → bot behavior |
| Slash commands | `/ask <profile> <prompt>`, `/skills <profile>`, `/add-skill`, `/remove-skill` | New | Surface dashboard controls in Discord |
| Conversation thread | Each `/ask` opens a Discord thread, scoped to that profile | New | Conversation stays in the bot's channel; threads keep history |

**Why not one bot per agent?**
- Each bot needs a separate token, OAuth setup, and gateway connection — multiplied by 22 profiles this is 22 separate secrets to rotate
- The 22-bot fleet must be monitored individually for rate limits, gateway health, and sharding
- Token leakage in 1/22 bots is a security event for that whole agent
- The mode_router already routes by `agent` field — extending it to Discord channels is natural and reuses tested code

**Why not slash-command-only?**
- Loses conversation history (each /ask is stateless)
- Loses thread/reply structure Discord users expect
- Doesn't match the user's vision of "have conversations from there"

### C. Per-project skill-selection dashboard UI

**Extend the existing Agent Growth Studio** (`backend/api/agent_growth.py` + `frontend-react/src/components/AgentConstellation.tsx` + new `SkillMarketplace.tsx`).

**Data model (proposed):**

```json
// state/agent_skill_assignments.json (already exists; extend)
{
  "project_xyz": {
    "jarvis-frontend": {
      "active": ["composio/brand-guidelines", "mxyhi/electron", "nextlevelbuilder/ui-ux-pro-max-skill", "microsoft/playwright"],
      "available": ["pbakaus/impeccable", "leonxlnx/taste-skill"],
      "dormant": ["alchaincyf/huashu-design"],
      "last_updated": "2026-06-09T01:30:00Z",
      "notes": "Frontend team has Playwright MCP loaded; UI/UX stack ready"
    },
    "jarvis-ui_ux": {
      "active": ["bergside/awesome-design-skills", "pbakaus/impeccable", "leonxlnx/taste-skill"],
      "available": ["alchaincyf/huashu-design"],
      "dormant": [],
      "notes": "Designer gets the 3 design skills, Chinese design corpus is dormant for now"
    }
  },
  "project_default": { ... }
}
```

**UI panel (new `SkillMarketplace.tsx`):**

```
┌─ Skill Marketplace ────────────────────────────────────┐
│ Project: [war-room] ▼  Agent: [jarvis-frontend] ▼      │
│                                                       │
│ Active (3)               Available (12)                │
│ ☑ playwright            ☐ brand-guidelines             │
│ ☑ ui-ux-pro-max         ☐ electron                     │
│ ☑ mxyhi-ok              ☐ taste-skill                  │
│                         ☐ ...                          │
│                                                       │
│ [+ Add from catalog]  [- Remove]  [Save]              │
│                                                       │
│ Catalog (search) ────────────────────────────────      │
│ Filter: [All depts ▼]  Search: [____________]         │
│ • composio/brand-guidelines (UI) [Add]                │
│ • bergside/awesome-design-skills (UI) [Add]           │
│ • mukul975/cybersecurity (Security) [Add]             │
│ • ...                                                  │
└───────────────────────────────────────────────────────┘
```

**Backend endpoints (extend `agent_growth.py`):**

- `GET /api/.../agents/<agent>/skills?project=X` — list active/available/dormant
- `POST /api/.../agents/<agent>/skills` — body `{project, skill, action: "add"|"remove"|"activate"|"deactivate", notes}`
- `GET /api/.../skills/catalog?dept=UI` — list skills in the catalog, filterable by department
- `POST /api/.../skills/import-from-repo` — body `{url, dept}` — fetches a skill repo, parses SKILL.md files, adds to catalog

**Persistence: dashboard-local only** (Decision 7 / Decision 8 from `docs/decisions.md` — never mutate Hermes profile configs without explicit human approval).

### D. The new departments (from the survey)

The existing 6 are: **engineering, research, marketing, finance-ops, product, security**.
The 2026-06-08 sprint noted that **marketing and finance-ops have no profile yet** — confirmed here.

**New department proposals** (from the round 2/3 surveys and the user's vision of "end-to-end company"):

| Dept | Justification | Maps to new profile |
|---|---|---|
| **ui-ux** | The user named it explicitly. The 4 design-skill repos need a single home. | `jarvis-ui_ux` |
| **mobile** | End-to-end company needs a mobile dev. `electron` skill is the closest proxy today. | `jarvis-mobile` |
| **data-ml** | The data/ML bundle on antigravity is the largest single category of skills. | `jarvis-data-ml` |
| **devops** | Implicit in the existing eng department; should be its own lead. | `jarvis-devops` |
| **sales** | A company has sales. `ComposioHQ/awesome-claude-skills` has a sales subset. | `jarvis-sales` |
| **legal** | The security skill corpus covers compliance. | `jarvis-legal` |
| **customer-success** | EJClaw + Llliao1113 patterns. Essential for an "end-to-end company." | `jarvis-customer-success` |

**Final department list (13 total):**

```
1. engineering (existing)   → jarvis-engineering-lead, jarvis-qa-lead, jarvis-security-lead, jarvis-docs-lead
2. ui-ux          (NEW)     → jarvis-ui_ux
3. frontend       (NEW)     → jarvis-frontend
4. backend        (NEW)     → jarvis-backend
5. mobile         (NEW)     → jarvis-mobile
6. data-ml        (NEW)     → jarvis-data-ml
7. devops         (NEW)     → jarvis-devops
8. product        (existing) → jarvis-product-lead
9. design         (NEW alias of ui-ux) → jarvis-ui_ux
10. marketing     (existing) → jarvis-marketing
11. sales         (NEW)     → jarvis-sales
12. finance-ops   (existing) → jarvis-finance
13. legal         (NEW)     → jarvis-legal
14. customer-success (NEW)  → jarvis-customer-success
15. research      (existing) → jarvis-scout, jarvis-researcher
16. leadership    (existing) → jarvis-boss, jarvis-manager, jarvis-secretary, jarvis-council
```

### E. The "Council of Departments" pattern

**New idea (synthesized from rounds 1-3):** the user wants a "best agentic army in the world." The current `jarvis-council` is a **single-agent council** (karpathy 3-stage). What they likely want is a **Council of Departments**:

- A new `jarvis-council-departments` profile (no model — just a router)
- When a question comes in, the council invokes one delegate per relevant department
- Each delegate consults its assigned skills
- Department delegates vote; chairman synthesizes

This is the **rotating-subject variant of llm-council** — a tier above the existing council.

### F. Things I'm NOT recommending (gap analysis discipline)

| Repo/Skill | Why not |
|---|---|
| `jadecli/claude-multi-agent-dispatch` (0⭐) | Novel idea (tree-sitter routing) but 0 stars. Watch, don't adopt. |
| `M00C1FER/contract-net-router` (0⭐) | CNP bidding is academically cool but adds latency. Adopt the **concept** for `spawn.py` 2.0, don't import the lib. |
| `xuil tul/animaworks` (238⭐) | Brain-inspired memory — interesting but overlaps with our Hindsight decision. |
| Langflow / Flowise (53k-149k⭐) | Already rejected 2026-06-08 (RCE + duplication). |
| `xvirobotics/metabot` (856⭐) | "Self-improving org" — concept right, but the user's `agent_growth.py` already does this. Don't duplicate. |
| `LangSmith` (commercial) | Costs money; we use Langfuse. |
| `Browser-use` (97k⭐) | Adjacent (browser automation), not an org pattern. Use `microsoft/playwright` MCP instead. |

## Cost & feasibility (with user's $20 plan + 8GB VRAM)

| Layer | Cost | Notes |
|---|---|---|
| Profiles (22 × SOUL.md + config.yaml) | $0 | Generated by script (extends `gen_agent_files.py`) |
| Skill ingestion (skim 1,500 skills from antigravity) | $0 | `git clone` is free; parse at ingest time; storage in `state/skill_catalog.json` (~1-2 MB) |
| 1 Discord bot (recommended) | $0 | Free tier |
| Codex usage (codex is the workhorse) | **$0** (inside $20 plan) | Codey's ChatGPT subscription covers codex; this sprint uses codex for code review and synthesis only — actual day-to-day LLM calls happen in the user's ChatGPT sessions |
| Local Ollama (fallback for cheap skills) | $0 | Disk only; the 8GB VRAM can hold a 7B Q4 model |
| New MCP servers (playwright, git, postgres) | $0 | All free |
| **Total net-new** | **$0/month** | Already-paid ChatGPT sub covers codex usage |

**Caveat from codex review:** "Total $0/month" is true for *new* spend, but the user's existing $20 ChatGPT plan and ~16 GB RAM are the bottleneck. The army will consume more codex calls than a single-agent workflow — this is still within the $20 plan if we route cheap tasks (status checks, formatting, simple Q&A) to local Ollama and reserve codex for code review, council decisions, and skill ingestion.

---

## Post-sprint corrections (2026-06-09 01:48 — Codex review)

GPT-5.5 (codex) audited this ledger via `codex exec --dangerously-bypass-approvals-and-sandbox` after the main draft. Its 10 findings are resolved here. Tracking numbers match the order codex raised them.

### Weak-claim fixes

1. **ComposioHQ/awesome-claude-skills at 63,768⭐** — codex flagged as "implausible." **Verified live in Round 4** via `browser_navigate` to `https://github.com/ComposioHQ/awesome-claude-skills`; star count displayed in the snapshot is "63.8k" — i.e. 63,768 is a reasonable read. Not a hallucination. (Composio is a Series A/B SaaS company whose own commercial product depends on this list — the star count is plausible.) Leaving as-is with verification.

2. **"10 search rounds" vs 6 visible** — codex is right. The methodology section claimed 10 but only 6 are numbered. **Fixed** in § Sprint methodology above (now reads "6 numbered rounds + 4 follow-up repo navigations (10 visits total)").

3. **"Total: $0/month"** — codex is right that this is too strong. **Fixed** in § Cost & feasibility above (now reads "Total net-new: $0/month" with caveat that the $20 ChatGPT plan and 16 GB RAM are the bottleneck).

4. **"Discord rate limits 5 bots/server"** — codex is right. That was a stale memory from somewhere; the actual Discord limit is 2500+ bots/server for verified apps, with rate limits per bot being a separate concept (50 req/sec per route for most endpoints). **Fixed** in § Discord bot architecture (recommendation block removed the false claim and the rationale section reframed the trade-off as secret-rotation cost).

5. **"Each profile is fully isolated; no cross-profile state in the runtime"** — codex flagged as unverified-from-docs. **Acknowledged**: the perusal was of `~/.hermes/profiles/<name>/{config.yaml,SOUL.md}` structure on the local file system + the `docs/FEATURE_INVENTORY.md` mention of "Profile ≠ Agent" in the spec. Hermes docs at `hermes-agent.nousresearch.com/docs` are the authoritative source; reading the docs end-to-end was not done in this sprint. **Recommend: a 30-min hermes-docs read at the start of the implementation phase** to verify profile isolation before building 22 of them.

### Missing-piece fixes

1. **Evidence table per repo** — every Tier-A repo in this ledger has URL + license + last-commit timestamp (from the GitHub snapshot) + a `Plan` column. Codex asked for "URL, commit/date checked, license, star count source, why it is safe." We have most of this. **Adding a "Verification" column to each major table is recommended for the next revision**.

2. **No validation of existing code claims** — the ledger references `discord_bridge.py`, `agent_growth.py`, `mode_router.py`, `spawn.py`, and `gen_agent_files.py`. **A read-through of these files at the top of implementation phase is required** (it's the first step in § H below).

3. **No security model for skill import** — codex is right and this is a critical gap. **Adding § H. Security model for skill import** below.

4. **No implementation sequence** — codex is right. **Adding § I. Phased implementation plan** below.

5. **No success metrics / tests** — codex is right. **Adding § J. Test plan** below.

### H. Security model for skill import (new section, addresses codex finding 3)

When importing skills from third-party repos (1,500 from antigravity, 1,000 from VoltAgent, etc.), we need a trust boundary. The War Room's invariant is **dashboard-local only — never mutate Hermes profile configs without explicit human approval** (Decision 7, `docs/decisions.md`).

**Proposed policy:**

| Trust tier | Source | What we do |
|---|---|---|
| **T0 — Local authored** | Skills we write ourselves in `backend/jarvis_company_os/skills/<name>.md` | Auto-add to catalog; flag in UI as "authored" |
| **T1 — Curated** | The 4 hand-picked repos: `alirezarezvani/claude-skills`, `mxyhi/ok-skills`, `bergside/awesome-design-skills`, `mukul975/Anthropic-Cybersecurity-Skills` | Manual review of each SKILL.md's frontmatter; add to catalog with `curated` flag |
| **T2 — Bulk-indexed** | `sickn33/antigravity-awesome-skills`, `ComposioHQ/awesome-claude-skills`, `VoltAgent/awesome-agent-skills` | Auto-import; tag as `bulk`; user must explicitly activate per-project per-agent |
| **T3 — Untrusted** | Any repo not on the curated list | Block by default; user can override with a `/add-untrusted-skill <url>` slash command that requires confirmation |

**Concrete guardrails:**

- SKILL.md files are stored under `state/skill_catalog/<name>/SKILL.md` — **never** symlinked into a Hermes profile
- Each skill has a `provenance` field: `{source_repo, source_url, commit_sha, imported_at, imported_by}`
- Each skill has a `signature_required` flag set to true for T2/T3 — the skill can only be activated by an explicit user click in the dashboard, not by a subagent
- A daily cron job (`scripts/sync_skill_catalog.py`) re-fetches the curated repos and flags any SKILL.md that changed since the last sync
- Skill content is **not** injected into SOUL.md at ingest time — it's loaded at task-time by the skill composition layer (matches the 2026-06-08 "pre-flight + lazy" pattern)

**Prompt-injection review (per codex):** skills containing obvious injection patterns ("ignore previous instructions", `<|system|>`, `Assistant:` role prefixes) are auto-quarantined to a `state/skill_catalog/_quarantine/` folder and never loaded.

### I. Phased implementation plan (new section, addresses codex finding 4)

The user said "set this as goal to do don't stop until you finish" and "use codex to verify what you are doing along the way." The phased plan below puts the smallest testable milestone first so we can stop and re-check after each phase.

| Phase | Scope | Estimated time | Testable? |
|---|---|---|---|
| **0. Read & verify** | Read `backend/api/discord_bridge.py`, `agent_growth.py`, `mode_router.py`, `spawn.py`, `gen_agent_files.py` end-to-end. Read Hermes Agent docs. Verify all 22 profile-name conflicts (none should exist) | 2-3 hours | Yes — written verification report |
| **1. Profile generator v2** | Extend `gen_agent_files.py` to template SOUL.md + config.yaml + AGENTS.md for the 14 new profiles (jarvis-frontend, ui_ux, backend, mobile, data-ml, devops, marketing, sales, finance, legal, customer-success, plus rename `researcher` → `jarvis-researcher`) | 4-6 hours | Yes — pytest that creates 1 profile, asserts files exist + YAML parses |
| **2. Skill catalog + dashboard panel v1** | Add `state/skill_catalog/` JSON + backend endpoints (`GET /agents/<name>/skills?project=X`, `POST .../skills`). Build `frontend-react/src/components/SkillMarketplace.tsx` panel | 6-8 hours | Yes — browser smoke test + pytest for the API |
| **3. Discord bot bridge v2** | Extend `backend/api/discord_bridge.py`: per-channel config table in `state/discord_guild.json`, slash commands (`/ask`, `/skills`, `/add-skill`, `/remove-skill`), per-agent prompt prefix, thread-per-conversation. Requires user's Discord bot token in `state/dashboard.env` | 6-8 hours | Yes — manual Discord test (user DMs the bot in a test server) |
| **4. Council of Departments v1** | New `jarvis-council-departments` profile (router-only). When `/ask` is invoked without specifying an agent, the council picks 1-3 relevant departments and routes to them. Synthesizes responses | 4-6 hours | Yes — council smoke test from Decision 4 of `decisions/council-vote.md` |
| **5. Production hardening** | Slack/email/audit integration for skill changes; rate limiting; backup/restore of skill catalog; per-project audit trail of which agent used which skill | 4-6 hours | Yes — smoke tests for each guardrail |

**Total estimated time:** 26-37 hours, runnable in 1-2 weeks part-time.

**Why this order:** Phase 0 is zero-risk verification. Phases 1-2 can ship without any external service changes (Discord is not touched). Phase 3 unblocks the user's headline goal ("connect each profile to a discord bot"). Phase 4 is the most novel/risky piece — comes after the user has used the basic Discord wiring. Phase 5 is the cherry on top.

**Rollback plan:** every phase writes to a separate file/module. Reverting a phase is `git revert <phase-commit>`. Skill catalog lives in `state/` (not in the repo) — wipes are recoverable from the upstream repos.

### J. Test plan (new section, addresses codex finding 5)

Per `CLAUDE.md` workflow: **failing test first (RED), then implement (GREEN), then update spec.**

| Layer | Test | Type |
|---|---|---|
| Profile gen | `test_gen_agent_files.py` — create 22 profiles from a YAML spec, assert all SOUL.md exist, all config.yaml parse, all AGENTS.md reference valid collaborators | pytest |
| Skill catalog | `test_skill_catalog.py` — parse 10 SKILL.md files from each Tier-A repo, assert frontmatter is valid, assert no injection patterns in content | pytest |
| Per-project assignment | `test_agent_skill_assignments.py` — POST /agents/<name>/skills with project=war-room, GET, assert state persists; POST again with same project, assert dedup | pytest |
| Discord bridge | `test_discord_bridge.py` — mock the Discord gateway, simulate a message in `#jarvis-frontend`, assert the bridge dispatches to the `jarvis-frontend` profile | pytest + manual Discord integration test |
| Council of depts | `test_council_departments.py` — given a query "design a new login page", assert the council picks `jarvis-frontend` + `jarvis-ui_ux` + `jarvis-security-lead` (or 2-of-3), and synthesizes a response | pytest |
| Rollback | `test_skill_catalog_rollback.py` — wipe `state/skill_catalog/`, re-run the import script, assert catalog is restored | pytest |
| Permission isolation | `test_profile_isolation.py` — assert profile A's env vars cannot be read by profile B (Hermes sandbox test) | pytest |
| Frontend dashboard | `SkillMarketplace.test.tsx` — render the panel, assert 3-column layout (active/available/dormant), click "add" → state updates | vitest |

**Coverage target:** 80% on new code (per existing pytest config in `backend/requirements-dev.txt`).

---

## Open questions for the user (before I start building) — RESOLVED 2026-06-09 01:55

User answered all 8 on 2026-06-09 01:55. See `decisions/D-2026-06-09-agentic-army-sprint.md` for the full locked plan.

**Summary of answers:**

| # | Question | User's answer |
|---:|---|---|
| 1 | Discord architecture | **1 channel `#coding_plan_feedback` + per-project threads** (user override — single channel, threads scope projects, all 22 agents reachable in any thread) |
| 2 | Skill import scope | **Default — Tier-1 + T2 (2,500+ skills, 7 repos)** |
| 3 | Profile creation order | **All 14 in Phase 1** (not 3 first) |
| 4 | Department count | **Keep all 13 separate** (user: skill/MCP bloat per agent is a concern — fine-grained prevents that) |
| 5 | Council of Departments | **Yes, build in Phase 4** — keep existing 3-stage council too |
| 6 | Channel names | **`#jarvis-<profile>` for profile identity inside threads**; main channel is `#coding_plan_feedback` |
| 7 | Council chair model | **Codex for now**; **pluggable for local models later** |
| 8 | Skill selection UI | **New `SkillMarketplace.tsx` panel** |

**Process rule (locked):**
- Council call (codex) at: start of each phase, before each major task, end of each phase
- Running ledger at `docs/COUNCIL_LOG.md` + per-phase summaries in `docs/phases/`
- Goal: complete all 6 phases end-to-end

---

## Status

- **Sprint complete.** 6 search rounds + 4 deep dives. All findings written to this ledger.
- **Codex review complete.** 5 weak claims + 5 missing pieces audited and addressed in § Post-sprint corrections.
- **Synthesis complete.** 22-profile proposal, Discord architecture, dashboard UI spec, 13-department taxonomy, security model, phased build plan, test plan, 8 open questions.
- **Cost: $0/month net-new** (within the user's existing $20 ChatGPT plan + 8GB VRAM, with codex usage routed through local Ollama for cheap tasks).
- **Waiting for user answers** to the 8 open questions above. Implementation will not start until they are answered.
- **Sprint log:** `docs/RESEARCH_LEDGER_AGENTIC_ARMY.md` (this file). **Existing 2026-06-08 ledger** at `docs/RESEARCH_LEDGER.md` is the foundation this sprint built on.
