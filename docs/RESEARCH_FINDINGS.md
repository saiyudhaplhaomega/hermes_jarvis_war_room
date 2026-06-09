# RESEARCH FINDINGS — Master Synthesis

**Date:** 2026-06-08
**Scope:** 5 loops × 10 rounds = 50 rounds of research
**Council:** 50 codex (gpt-5.5) consultations + 50 ollama (qwen2.5:3b) verifications
**Reference repos cloned:** 4 (MiroFish-Offline, llm-council, AI-CoScientist, claude-skills)
**Status:** Complete. Ready for the user to "proceed from here."

---

## TL;DR

War Room should evolve from **"13+ named agents in a FastAPI dashboard"** into **"a self-improving, council-routed, memory-rich, deck-style control room for an AI company."** The research surfaced 5 architectural decisions, 12 specific tool picks, and a Department Starter Kit skeleton that gets us there without adding monthly cost.

**Cost target:** $0/month (all picks are self-hostable, MIT/Apache-2.0/BSD; 1 license flag noted).

**The single biggest finding:** War Room has the **org chart** but not the **management protocol**. Adding decision rights, handoff schemas, escalation rules, and a skill marketplace transforms it from a kanban-with-agents into a real AI company operating system.

---

## The 5 Loops at a glance

| Loop | Theme | Key pick(s) | Verdict |
|---|---|---|---|
| **1** | Memory systems | Hindsight + mem0 v3 + Graphiti | 3-tier, $0, 2 license traps |
| **2** | MiroFish-style research | STORM + DeerFlow + smolagents | Adapt 5-stage, role-split primary |
| **3** | LLM Council | karpathy/llm-council 3-stage + Chairman=role | Adopt for strategic only |
| **4** | Departments | claude-skills structure | Adopt 6-dept starter kit |
| **5** | Dashboard | Langfuse + xyflow 2D + R3F 3D + n8n | 5-pattern library |

---

## Cross-cutting findings (the ones that matter most)

### Finding 1 — The 3-tier memory architecture
- **Hot (per-agent, in-process):** Hindsight embedded (`hindsight-all` pip install) for state-of-mind
- **Warm (project-level):** mem0 v3 (facts) + Chroma (vectors) + FalkorDB-Lite (graph) + Graphiti (temporal)
- **Cold (global):** Qdrant + FalkorDB server + Graphiti via MCP
- All $0. 2 license flags: **FalkorDB is SSPLv1** (blocks SaaS redistribution; fine for self-host) and **mem0 cloud is paid** (we use self-host).
- See `docs/research/loop-1-summary.md` for the full 10-row "which data type → which backend" matrix.

### Finding 2 — The Pipeline Pattern (Loop 2)
War Room should adopt MiroFish's 5-stage *structure* (intake → context graph → agent briefing → simulation/council → report → chat/actions), but **skip persona generation** (we have 13+ persistent named agents). Add **STORM's perspective-guided questioning** as an optional `perspective_guided=true` research mode. Add **DeerFlow's role split** (Planner/Researcher/Coder/Reporter). Wrap a single **smolagents CodeAgent** in those roles for execution. **AI-CoScientist** provides tournament-based hypothesis ranking, but never trust Elo alone — always need human approval for research direction changes.

### Finding 3 — The Council Charter (Loop 3)
- **Adopt karpathy's 3-stage for strategic decisions only**: parallel independent → anonymized ranking by criteria → chairman synthesis with minority warnings preserved
- **Chairman is a role, not a model** — any capable model plays it, prompt rules define behavior
- **Third-party judge by default** (a model not in the debate)
- **Confidence scoring:** sample 2-3×, extract key claim, compare. Don't trust logprobs alone.
- **Failure modes to actively prevent:** groupthink, authority bias, error amplification, cost/latency blowup
- **Cost-aware routing:** task-routing classifier → cheap-first → escalation on failure
- **qwen2.5:3b is too weak** to be a real second opinion. **Pull a 7B or Nemotron.**
- **Operational checklist:** version + freeze everything, disagreement handling, per-model metrics, full audit trail, weekly council eval

### Finding 4 — The Management Protocol (Loop 4) ⭐
**This is the biggest gap.** War Room has 13+ named agents and a FastAPI hierarchy but no:
- Decision rights per tier
- Handoff schemas (Worker→Lead, Lead→Manager, Manager→Boss)
- Escalation rules (blocker, threshold breach, NOT by default)
- Task lifecycle states (draft → ready → in_progress → blocked → review → done → archived)
- Success criteria per task type
- After-action learning loops

**The 6-department starter kit** (adapted from `alirezarezvani/claude-skills`):

| Dept | Files | Maps to existing War Room roles |
|---|---|---|
| **Engineering** | SOUL, TOOLS, AGENTS, CONVENTIONS, POSTMORTEMS | eng-lead + qa-lead + security-lead |
| **Research** | SOUL, METHODS, SOURCES, SYNTHESES, AGENTS | scout + researcher |
| **Marketing** | SOUL, BRAND, CAMPAIGNS, ASSETS, METRICS | **(missing — add)** |
| **Finance/Ops** | SOUL, BUDGETS, RUNBOOKS, INCIDENTS, AGENTS | **(ops-lead missing — add)** |
| **Product** | SOUL, ROADMAP, REQUIREMENTS, AGENTS, DECISIONS | product-lead |
| **Security** | SOUL, THREAT_MODEL, CONTROLS, INCIDENTS, AGENTS | security-lead |

**Skill marketplace pattern:** separate `skills/*.md` files (NOT inline in SOUL.md) + a `skills/registry.json`. Stay compatible with `npx skills add <repo>`. **Pre-flight selection (router picks 2-3) + lazy activation** as the composition strategy.

**Anthropic's 5 workflow patterns** → 5 War Room desks:
- Prompt chaining → Strategy Desk
- Routing → Triage Desk
- Parallelization → Intelligence Cell
- Orchestrator-workers → Command Center
- Evaluator-optimizer → Red Team / QA Desk

**Always ask first:** "could this be a single LLM call?" If yes, don't spin up a department.

### Finding 5 — The Dashboard Pattern Library (Loop 5)
**5 patterns for every War Room panel:**
1. **Real-time** — snapshot+delta over WebSocket (NOT full event stream). Topic subscriptions.
2. **Observability** — Langfuse (default) + OpenLLMetry/OTel (portable). Phoenix for eval.
3. **Command-deck** — 3D centerpiece (AgentConstellation) + dense tactical surfaces (KanbanFleet, ArmyOperations) + gutter logs (AuditStrip)
4. **Command center UX** — scanning/triage/comparison over presentation
5. **Default editor mode** — 2D xyflow for topology authoring (precision). 3D R3F for status (presence). Same data model, both views.

**Tool decisions:**
- ✅ **Adopt:** Langfuse (observability), xyflow (2D editor), R3F (3D viz), OTel (standard)
- ⚠️ **Boundary:** n8n (already running) = automation/action layer; War Room = reasoning/org control
- ❌ **Skip:** LangSmith (commercial), LangFlow/Flowise (RCE history + duplication), VectorShift/Vellum (no-code = vendor coupling)

---

## The 12 tool picks (consolidated)

| # | Tool | Tier | Purpose | License | Action |
|---|---|---|---|---|---|
| 1 | **Hindsight** (vectorize-io) | Hot memory | State-of-mind, learning | MIT | `pip install hindsight-all` |
| 2 | **mem0 v3** (mem0ai) | Warm facts | Factual memory, multi-signal retrieval | Apache-2.0 | Self-host Docker |
| 3 | **Graphiti** (getzep) | Temporal | Context graphs with validity windows | Apache-2.0 | Docker + MCP |
| 4 | **Chroma** | Warm vector | Embedded vector DB | Apache-2.0 | `pip install chromadb` |
| 5 | **Qdrant** | Cold vector | Production vector DB | Apache-2.0 | Docker (cluster) |
| 6 | **FalkorDB-Lite / server** | Graph | Multi-tenant graph | SSPLv1 ⚠️ | Docker, watch license |
| 7 | **STORM** (stanford-oval) | Research | Perspective-guided questioning | MIT | `perspective_guided=true` mode |
| 8 | **DeerFlow** (bytedance) | Research | Planner/Researcher/Coder/Reporter roles | MIT | Borrow roles, skip UI |
| 9 | **smolagents** (HuggingFace) | Execution | Single CodeAgent | Apache-2.0 | Wrap in DeerFlow roles |
| 10 | **karpathy/llm-council** | Council | 3-stage strategic voting | MIT gist | Use for strategic only |
| 11 | **Langfuse** | Observability | LLM traces, scores, datasets | MIT + commercial | Self-host, $0 |
| 12 | **@xyflow/react** + **R3F** | Visualization | 2D editor + 3D status | MIT | `npm install` |

**Plus the existing stack** (already in repo): FastAPI, React 19, Vite, Tailwind 4, Playfair/Framer Motion patterns. **Plus the user's existing tooling:** n8n (Docker), ChatGPT sub, Claude sub, Codex CLI, Ollama (qwen2.5:3b), Hermes, Cursor.

---

## Implementation phases (proposed, from here)

### Phase A — Foundation (this week)
- ✅ Topology editor v1 sub-phase 1 (RED→GREEN) — **DONE** in this session
- 🔲 Topology editor v1 sub-phase 2 — the React component, 2D xyflow
- 🔲 Decision Brief v2 (`D-2026-06-08-topology-editor.md`) — user approval

### Phase B — Memory (next 1-2 weeks)
- 🔲 Memory M1: wire mem0 + Hindsight into `backend/core/`
- 🔲 Memory M2: Chroma + FalkorDB-Lite project-level
- 🔲 Memory M3: Qdrant + FalkorDB server + Graphiti MCP global
- 🔲 llm-wiki vault at `~/wiki/` (Obsidian viewer)

### Phase C — Council (parallel with B)
- 🔲 Pull a 7B or Nemotron for second opinion
- 🔲 Implement the 3-stage council pattern in `backend/api/council/`
- 🔲 Wire chairman=role, third-party judge, confidence sampling

### Phase D — Departments (after C)
- 🔲 Build the 6-dept starter kit (6 folders, 30+ files)
- 🔲 Add `ops-lead` and dedicated `researcher` agents
- 🔲 Codify escalation policy + management protocol
- 🔲 Skill marketplace with `skills/registry.json`

### Phase E — Dashboard (after D)
- 🔲 Langfuse integration
- 🔲 WebSocket snapshot+delta upgrade
- 🔲 2D xyflow topology editor (sub-phase 2, 3, 4)
- 🔲 3D constellation upgrades (R3F)
- 🔲 n8n webhook bridges

### Defer (Phase F+)
- 🔲 Letta — only if agent loop exceeds 32k tokens
- 🔲 Cognee — only if maintaining 3 backends becomes painful
- 🔲 LanceDB — only if we want to mix vectors with tabular
- 🔲 Vellum/VectorShift — only as prototype sidecar

---

## Risk register (the things that will hurt us if we ignore them)

1. **FalkorDB SSPLv1** — blocks SaaS redistribution. If we ever ship a hosted version, need commercial license. **Replacements ready:** Kuzu (MIT, embedded), Memgraph (BSL).
2. **mem0 cloud confusion** — easy to accidentally use the paid cloud instead of the free self-host. **Pin** in config.
3. **qwen2.5:3b too weak** — the 2-voice council today has one strong voice and one whisper. **Fix:** pull a 7B or Nemotron.
4. **LangFlow/Flowise RCE history** — both had serious executable-workflow vulnerabilities. **Don't expose in War Room.**
5. **Groupthink in councils** — even with the 3-stage pattern, if models are similar, they agree too easily. **Mitigation:** diverse model families, anonymized ranking, minority warnings.
6. **No management protocol** — biggest single risk. Without escalation/handoff rules, the org becomes a soup of agents with no accountability.
7. **Self-improvement without gates** — auto-pruning knowledge, auto-tuning prompts, etc. all need evaluation gates (per Loop 2 R9).

---

## The Department Starter Kit (the deliverable you asked for)

Inspired by `alirezarezvani/claude-skills` (30+ departments), the War Room gets 6 starter departments. **Each folder structure:**

```
backend/jarvis_company_os/departments/
├── engineering/
│   ├── SOUL.md           # identity, principles, voice
│   ├── TOOLS.md          # what tools it can use
│   ├── AGENTS.md         # who it reports to / peers
│   ├── CONVENTIONS.md    # do/don't
│   └── POSTMORTEMS.md    # after-action reports
├── research/
│   ├── SOUL.md
│   ├── METHODS.md
│   ├── SOURCES.md
│   ├── SYNTHESES.md
│   └── AGENTS.md
├── marketing/            # NEW — add this
│   ├── SOUL.md
│   ├── BRAND.md
│   ├── CAMPAIGNS.md
│   ├── ASSETS.md
│   └── METRICS.md
├── finance-ops/          # NEW — add this
│   ├── SOUL.md
│   ├── BUDGETS.md
│   ├── RUNBOOKS.md
│   ├── INCIDENTS.md
│   └── AGENTS.md
├── product/
│   ├── SOUL.md
│   ├── ROADMAP.md
│   ├── REQUIREMENTS.md
│   ├── AGENTS.md
│   └── DECISIONS.md
└── security/
    ├── SOUL.md
    ├── THREAT_MODEL.md
    ├── CONTROLS.md
    ├── INCIDENTS.md
    └── AGENTS.md
```

**Plus the top-level skills marketplace:**

```
backend/jarvis_company_os/skills/
├── registry.json         # name, purpose, triggers, tools, maturity
├── README.md
└── <skill_name>.md       # one file per skill
```

**Plus the escalation policy:**

```
backend/jarvis_company_os/policies/
└── escalation_policy.md
```

---

## The Master Decision Matrix (the punchline table)

| Question | Answer | Source |
|---|---|---|
| Which memory for facts? | mem0 v3 | Loop 1 R2 |
| Which memory for learning? | Hindsight | Loop 1 R1 |
| Which memory for temporal? | Graphiti | Loop 1 R3 |
| Which vector DB? | Chroma (warm) + Qdrant (cold) | Loop 1 R7 |
| Which graph DB? | FalkorDB (watch SSPL) | Loop 1 R5 |
| Which research pattern? | STORM perspective + DeerFlow roles + smolagents execution | Loop 2 R2,4,5 |
| Which council pattern? | 3-stage (parallel→rank→chairman) | Loop 3 R1 |
| Who judges? | Third-party judge by default | Loop 3 R3 |
| Chairman = ? | Role, not model | Loop 3 R5 |
| When to escalate? | On blocker or threshold breach | Loop 4 R8 |
| Skill composition? | Pre-flight 2-3 + lazy activation | Loop 4 R10 |
| 2D vs 3D? | Split: 3D status, 2D editor | Loop 5 R9 |
| WebSocket pattern? | Snapshot + delta, topic subs | Loop 5 R7 |
| Observability? | Langfuse + OTel | Loop 5 R2 |
| Dashboard style? | Star/warp shell + tactical density | Loop 5 R8 |
| n8n role? | Automation layer, not brain | Loop 5 R5 |
| Department structure? | 6-dept starter kit | Loop 4 R2,R9 |

---

## Council self-assessment

**What 50 rounds taught us:**
- The research confirmed our existing memory + topology + decision-brief work is on the right track
- The biggest gap is **management protocol**, not tools — the org needs decision rights and escalation rules more than another DB
- The 2-voice council (codex + qwen2.5:3b) was useful but qwen2.5:3b often gave generic advice; **pulling a 7B or Nemotron is a clear next action**
- Most "popular" tools (LangFlow, Flowise, Vellum) are the wrong fit for War Room's code-first philosophy
- The cli's (codex, claude, ollama) all work — War Room has real multi-model muscle

**What the council disagreed on (smallest set):**
- MiroFish-Offline adoption: codex said "adapt structure", qwen said "use mix of persistent + disposable" — both compatible, we picked codex's framing
- Loop 5 R10: codex gave the right 5 patterns but had to be re-prompted; the initial answer was a confused template. Lesson: codex loses focus on checklist prompts; **structure the council prompt with a clear deliverable shape**

---

## Files to read next (in priority order)

1. **`docs/RESEARCH_FINDINGS.md`** ← you are here
2. **`docs/RESEARCH_LEDGER.md`** — all 50 rounds, raw findings
3. **`docs/research/loop-1-summary.md`** — memory strategy deep-dive
4. **`docs/research/topology-v1-sub-phase-1.md`** — today's implementation work
5. **`decisions/D-2026-06-08-topology-editor.md`** v2 — pending decision brief
6. **`docs/research/claude-skills/structure.md`** *(to be written)* — Department Starter Kit skeleton

---

## Next step: your call

Per your "after all the rounds and loops share what you found and we will proceed from there" — the research is done. The next move is yours. Suggested next moves, in priority order:

| Priority | What | Why | Effort |
|---|---|---|---|
| **P0** | Approve `D-2026-06-08-topology-editor.md` v2 | Sub-phase 1 already shipped; sub-phase 2 is the React component | 5 min decision |
| **P1** | Pull a 7B or Nemotron for the council | 3b is too weak to be a real second opinion | 5 min, ~5 GB |
| **P2** | Build Department Starter Kit (6 depts, 30+ files) | The biggest gap in the system | 1-2 days |
| **P3** | Wire mem0 + Hindsight (Memory M1) | Foundation for everything else | 1-2 days |
| **P4** | Topology editor v1 sub-phase 2 (2D xyflow) | The visual win that gets the new stack in front of you | 1 day |
| **P5** | Council 3-stage implementation | Strategic decision quality | 1-2 days |

Just say which P-level to start with.
