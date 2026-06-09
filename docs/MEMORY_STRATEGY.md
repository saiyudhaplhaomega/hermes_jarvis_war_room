# War Room Memory Strategy — Brainstorm + Combinations

Date: 2026-06-08
Author: Boss (research agent, Hermes)
Status: DRAFT for Saiyudh review
Project: Jarvis War Room Dashboard
Companion: `docs/RESEARCH_LEDGER.md` (full survey)

## TL;DR

There are **8 distinct kinds of memory** a multi-agent system like
ours needs. We currently have a **skeleton** (the gstack-derived
`backend/core/memory.py` with 4 trust tiers + half-life decay + a
promotion gate) but no real **storage** and no real **retrieval**.
This doc brainstorms the kinds, picks a free/open-source stack for
each, and tells you which to use at the project level vs the global
level.

The picks, in order of "adopt first":

| Layer | Project-level pick | Global-level pick | Cost |
|---|---|---|---|
| Episodic (raw conversation) | SQLite append-only `.jsonl` (we already do this for audit) | Same `.jsonl` partitioned by date | $0 |
| Vector (semantic recall) | **Chroma** (embedded, MIT) | **Qdrant** single-node (Apache-2.0) | $0 |
| Graph (relationships) | **FalkorDB-Lite** (embedded, BSD-3) | **FalkorDB** server (BSD-3) | $0 |
| Factual (memories extracted from episodes) | **mem0** self-hosted (Apache-2.0) | **mem0** self-hosted (same instance, multi-tenant) | $0 |
| Knowledge/wiki (curated, hand-written) | **llm-wiki** skill + Obsidian vault (MIT) | **llm-wiki** skill + shared vault | $0 |
| Procedural (SOUL.md / HEARTBEAT.md / TOOLS.md) | markdown files in `~/.hermes/profiles/<name>/` (already exist) | n/a — local only | $0 |
| State-of-mind (stateful agent loop) | **Letta** (MIT) — only if needed | n/a | $0 |
| Real-time temporal (time-decaying facts) | **Graphiti** (Apache-2.0) — only if needed | **Graphiti** | $0 |

**Net new cost: $0.** Every pick is free, self-hostable, MIT/BSD/Apache.

---

## Why this matters

Memory is where multi-agent systems fail. Every other piece of the
War Room (orchestration, dashboard, HITL, cost tracking) is
**routing** — the hard part is *remembering* and *reasoning over what
was remembered*. Three of our spec's "must not be faked" items
depend directly on memory:

- **Memory Nexus** (`frontend-react/src/components/MemoryNexus.tsx`)
  renders the double-helix memory view. Right now it visualizes
  *something*, but the underlying store is undefined.
- **Council Voting Record** — needs to know what was decided in the
  past, and which decisions still apply.
- **Cost/P&L per agent** — needs to know what each agent has done
  across its lifetime, not just today.

---

## 1. The 8 kinds of memory

These are conceptually distinct. A given agent may use 3-6 of them at
any time. **Don't conflate them.**

### 1.1 Episodic memory — "what just happened"

- **What it is:** the raw event log. Every message sent, every tool
  call, every approval. Time-ordered, append-only, immutable.
- **Why we need it:** the source of truth for everything else. Audit
  trail, replay, debugging, "show me what the CTO was doing Tuesday
  at 3pm."
- **Volume:** high (every LLM call = one episode).
- **Lifetime:** forever for audit, 30-90 days for hot retrieval.
- **Storage format:** newline-delimited JSON (`.jsonl`) is perfect.
  One line per episode. Easy to grep, replay, partition.
- **We already have this** for the audit strip
  (`backend/core/audit.py` + `audit.jsonl`).

### 1.2 Semantic (vector) memory — "find me the *similar* thing"

- **What it is:** embeddings of episodes / facts, retrieved by cosine
  similarity.
- **Why we need it:** "what did we decide about pricing last month?"
  won't have keyword overlap with the actual conversation — but
  *embedding* similarity will find it.
- **Volume:** medium (one embedding per episode summary, not per raw
  message).
- **Lifetime:** matches episodic.
- **Storage format:** vector DB (Chroma, Qdrant, Weaviate, Milvus,
  pgvector).
- **Watch out:** vector recall alone is not enough — it returns
  *similar*, not *correct*. Always pair with a trust tier / recency
  filter (we have the tier, we need to wire it up).

### 1.3 Graph memory — "how do X and Y relate?"

- **What it is:** a knowledge graph of entities (people, projects,
  decisions, components, agents) and the relationships between them.
- **Why we need it:** org-chart queries ("who is the eng-lead's
  reviewer?"), blast-radius analysis ("if this agent is offline, who
  is blocked?"), and the "edit topology" panel we just specced.
- **Volume:** medium (one node per entity, edges are cheap).
- **Lifetime:** forever — but merge on conflict.
- **Storage format:** graph DB (FalkorDB, Neo4j, Kuzu, Memgraph).
- **FalkorDB-Lite is embedded** — perfect for project-level. Full
  FalkorDB runs as a Docker container for global.

### 1.4 Factual memory — "things we believe to be true"

- **What it is:** extracted facts from episodes, each with a trust
  tier, source, and confidence. Examples:
  - "Saiyudh prefers bullet points over prose"
  - "War Room project uses CrewAI v1.14.7"
  - "The CTO model is `claude-sonnet-4-5`"
- **Why we need it:** the agent's "memory" in the colloquial sense.
  "What does the system know about X?"
- **Volume:** low (one fact per insight, deduplicated).
- **Lifetime:** long, but facts have a half-life (we already model
  this in `ConfidenceDecay`).
- **Storage format:** key-value or document store. Mem0 is purpose-built.
- **Watch out:** the *extraction* step is the hard part. Mem0, Cognee,
  Letta, Hindsight all do this differently. **Mem0** has the most
  momentum (58k stars, plugins for Claude/Codex/OpenCode/Cursor).

### 1.5 Knowledge / wiki memory — "the curated, human-approved record"

- **What it is:** hand-curated markdown. **llm-wiki** is the canonical
  implementation. The agent reads it, the human writes/reviews it.
- **Why we need it:** the source of truth for "this is how the system
  works." Episodes are messy; facts can be wrong; **the wiki is
  truth by decree.**
- **Volume:** small (dozens to hundreds of pages).
- **Lifetime:** forever; rotated and updated by humans.
- **Storage format:** markdown in `~/wiki/`, Obsidian-compatible.
- **We already have access to the skill** — `hermes skills` lists
  `llm-wiki`. We just need to point it at the War Room domain.

### 1.6 Procedural memory — "how to do X"

- **What it is:** the agent's instructions, tools, and behavior. In
  Hermes this is SOUL.md, HEARTBEAT.md, TOOLS.md, AGENTS.md.
- **Why we need it:** the agent is *defined* by its procedural memory.
  Without it, the agent has no role.
- **Volume:** small (per agent, 4-10 markdown files).
- **Lifetime:** forever, version-controlled.
- **Storage format:** markdown in `~/.hermes/profiles/<name>/`.
- **We already have this.** Spec section §3.4 says "every future
  agent should have SOUL.md, HEARTBEAT.md, TOOLS.md, and AGENTS.md."
  `backend/jarvis_company_os/gen_agent_files.py` is the generator.

### 1.7 State-of-mind (working) memory — "what's the agent thinking *right now*"

- **What it is:** the rolling scratchpad inside an agent's run. Where
  MemGPT / Letta / Hindsight shine. Core memory + archival memory +
  recall memory.
- **Why we need it:** an agent that has been running for an hour
  needs a way to summarize its current state, offload old context to
  archival, and recall on demand.
- **Volume:** small per session, scales with sessions.
- **Lifetime:** session-scoped, then archived.
- **Storage format:** purpose-built. **Letta** is the reference impl
  (was MemGPT). **Hindsight** is the new contender (16k stars, "Agent
  Memory That Learns", updated 8 min ago at the time of writing).
- **Watch out:** this is the layer most likely to be over-engineered.
  Start with mem0 + episodic; add Letta/Hindsight only if the agent
  loops actually need it.

### 1.8 Real-time temporal memory — "what's true *as of* timestamp T"

- **What it is:** facts with a validity window. "Saiyudh was using
  GPT-4 until 2026-05-01, then switched to Claude." Stored as a
  bi-temporal graph (event time + ingestion time).
- **Why we need it:** "what model was the eng-lead using when we
  deployed v1.4?" or "what was the company mission *at the time of
  this decision*?"
- **Volume:** medium.
- **Lifetime:** forever.
- **Storage format:** **Graphiti** (Apache-2.0, 27.2k stars) is
  purpose-built. Uses FalkorDB under the hood.
- **Watch out:** Graphiti is powerful but it's a graph DB underneath.
  Don't add it until you actually have bi-temporal queries. The 80/20
  win is mem0 + a `valid_from` / `valid_until` column.

---

## 2. The free / open-source shortlist (with what to use each for)

All 8 picks below are free, self-hostable, and active in 2025-2026.
Star counts and licenses verified at research time.

| Repo | ⭐ | License | What it does | When to pick it |
|---|---|---|---|---|
| **mem0ai/mem0** | 58.1k | Apache-2.0 | "Universal memory layer for AI Agents." Extracts facts from conversations, stores with trust tier. Has plugins for Claude, Codex, OpenCode, Cursor, VS Code | **Default pick for §1.4 (factual)**. Use it everywhere |
| **vectorize-io/hindsight** | 16k | Apache-2.0 | "Agent Memory That Learns." Bi-temporal, fact extraction, query-time learning | Pick if §1.7 (state-of-mind) becomes a bottleneck and §1.4 alone isn't enough |
| **getzep/graphiti** | 27.2k | Apache-2.0 | "Build Real-Time Knowledge Graphs for AI Agents." Bi-temporal graph over FalkorDB. Has MCP server | Pick if §1.8 (real-time temporal) is required |
| **letta-ai/letta** | 23.2k | MIT | MemGPT successor. Stateful agents with core/archival/recall memory tiers | Pick if the agent's *inner loop* needs a working memory (i.e., multi-hour runs with summarization) |
| **topoteretes/cognee** | 17.7k | Apache-2.0 | "Open-source AI memory platform for agents." Self-hosted knowledge graph + ECL (extract, cognify, load) pipeline | Pick if you want one tool that does §1.2 + §1.3 + §1.4 in one |
| **FalkorDB/FalkorDB** | 4.5k | BSD-3 | "The best Knowledge Graph for LLM (GraphRAG)." GraphBLAS-backed. **Embedded Lite version available** | Pick for §1.3 (graph). Use Lite project-level, full server global-level |
| **chroma-core/chroma** | 22k+ | Apache-2.0 | Embedded vector DB, simplest possible | Pick for §1.2 (vector) at project level. Zero ops |
| **qdrant/qdrant** | 24k+ | Apache-2.0 | Production vector DB, single binary, Rust | Pick for §1.2 (vector) at global level |
| **anthropics graphify** | (not public) | n/a | "Graphify" is a term used by Anthropic's docs for graph memory — there is no public `anthropics/graphify` repo. The user named it as inspiration; the practical replacement is **Graphiti** or **FalkorDB** + a small extraction layer | Treat as "the concept of graph memory," pick a concrete impl |
| **karpathy/llm-wiki** (gist) | n/a | n/a (gist, CC-BY-SA) | Karpathy's LLM Wiki pattern — interlinked markdown KB, raw/wiki/index/log 3 layers | Already loaded as a Hermes skill. Pick for §1.5 (knowledge/wiki) |

### What we're *not* picking (and why)

- **LangChain Memory** — coupled to the LangChain runtime; we have our
  own `jarvis_company_os`. Adopting it would mean a re-architecture.
- **Pinecone / Weaviate Cloud** — paid. We have Chroma and Qdrant.
- **Zep** (the old getzep/zep org) — Zep pivoted to Graphiti. Graphiti
  *is* the modern Zep.

---

## 3. The combination matrix — when to use what

This is the **decision table** for "what memory should an agent use
for this use-case?"

| Use-case | Episodic | Vector | Graph | Factual | Wiki | Procedural | State-of-mind | Temporal |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| "What did the CTO do today?" | ✅ | — | — | — | — | — | — | — |
| "What did the CTO say about X last week?" | ✅ | ✅ | — | — | — | — | — | ✅ |
| "Who is the CTO's reviewer?" | — | — | ✅ | — | — | — | — | — |
| "What model is the CTO using?" | — | — | ✅ | ✅ | — | ✅ | — | ✅ |
| "What does the system *believe* about pricing?" | — | — | — | ✅ | ✅ | — | — | — |
| "How should the CTO respond?" | — | — | — | — | — | ✅ | ✅ | — |
| "Why did we decide X?" | — | — | ✅ | — | ✅ | — | — | ✅ |
| "Show me the audit trail for run #42" | ✅ | — | — | — | — | — | — | — |
| "What does the team know that I forgot?" | — | ✅ | — | ✅ | — | — | — | — |
| "What was the eng-lead doing when we shipped v1.4?" | ✅ | — | ✅ | — | — | — | — | ✅ |

**Read this as: most queries touch 2-4 layers.** A single tool
won't do — the War Room will need a small memory router that fans a
query out to the right layers and stitches the answers.

---

## 4. Project-level vs Global-level — what to use where

This is the most important table in this doc. **It tells you which
storage to instantiate for a single War Room project vs the
multi-project global view.**

### 4.1 Project-level (one instance per War Room project)

A "project" = a focused area of work, e.g. `jarvis-dashboard`,
`skin-lesion-xai`, `crewMeld-bench`. Project context is
[PROTECTED] in our `FEATURE_INVENTORY.md` — every panel defaults to
the active project.

| Layer | Pick | Storage location | Why this pick |
|---|---|---|---|
| Episodic | `.jsonl` append-only | `state/projects/<slug>/episodes.jsonl` | Already what we do for audit. Zero deps. |
| Vector | **Chroma** embedded | `state/projects/<slug>/chroma/` | Embedded = no Docker. Per-project = clean isolation. |
| Graph | **FalkorDB-Lite** embedded | `state/projects/<slug>/falkordb/` | Embedded graph. Lightweight. |
| Factual | **mem0** with `user_id=<slug>` | `state/projects/<slug>/mem0/` or in-memory + Chroma | mem0 supports multi-tenant via user_id. |
| Wiki | **llm-wiki** vault | `state/projects/<slug>/wiki/` | One wiki per project. Compounded knowledge. |
| Procedural | markdown files | `~/.hermes/profiles/<agent>/` | Already there. Don't move. |
| State-of-mind | **Letta** (only if needed) | `state/projects/<slug>/letta/` | Skip until you have a use case |
| Temporal | **Graphiti** (only if needed) | `state/projects/<slug>/graphiti/` | Skip until you have bi-temporal queries |

**All 4 "active" picks (episodic, vector, graph, factual) are
file-based. Total disk per project: ~50-200 MB. Backs up with `tar`.
No Docker required at project level.**

### 4.2 Global-level (one instance, all projects)

A "global" memory is what persists *across* projects: "Saiyudh prefers
bullet points" is true no matter which project he's in. **Be
careful** — globals are powerful but they're the easiest way to leak
project-A secrets into project-B.

| Layer | Pick | Storage location | Why this pick |
|---|---|---|---|
| Episodic | `.jsonl` partitioned by date | `state/global/episodes/2026-06-08.jsonl` | Same format as project, just partitioned differently |
| Vector | **Qdrant** single-node | Docker container `qdrant` on `127.0.0.1:6333` | Production-grade, single binary. Multi-tenant via collection names. |
| Graph | **FalkorDB** server | Docker container `falkordb` on `127.0.0.1:6379` | Same as Lite but multi-user. Used by Graphiti. |
| Factual | **mem0** with `user_id=saiyudh` (single-tenant) | `state/global/mem0/` or in-memory + Qdrant | Same mem0 instance, but globally-scoped user_id |
| Wiki | **llm-wiki** shared vault | `state/global/wiki/` (with all project wikis as sub-folders) | One root vault, sub-vaults per project |
| Procedural | (not global) | — | Per-agent, never global |
| State-of-mind | (not global) | — | Per-agent |
| Temporal | **Graphiti** | Docker container, shared | One temporal graph for the whole company |

**Globals are 1-2 Docker containers** (Qdrant + FalkorDB) plus the
shared `state/global/` directory. Starts on `docker compose up`.

### 4.3 The "memory router" — a thin layer above

Don't expose 8 different memory APIs to the rest of the codebase.
Wrap them in a `MemoryRouter` (`backend/core/memory_router.py`)
with this signature:

```python
class MemoryRouter:
    async def recall(
        self,
        query: str,
        *,
        agent: str,
        project: str | None = None,
        layers: list[MemoryLayer] = [
            MemoryLayer.EPISODIC,
            MemoryLayer.VECTOR,
            MemoryLayer.GRAPH,
            MemoryLayer.FACTUAL,
            MemoryLayer.WIKI,
        ],
        max_per_layer: int = 5,
    ) -> RecallResult: ...
```

Each call:
1. Logs the query to episodic (`observed_at`, `agent`, `project`,
   `tier=OBSERVED` if it's a system call, `INFERRED` if it's a
   rehydrate).
2. Fans out to the requested layers.
3. Merges with simple RRF (reciprocal rank fusion) and applies the
   `PromotionGate` to filter untrusted facts.
4. Returns one ranked list to the caller.

**Writes go through a similar `MemoryWriter`:**

```python
class MemoryWriter:
    async def write(
        self,
        content: str,
        *,
        tier: TrustTier,
        agent: str,
        project: str | None = None,
        edges: list[tuple[str, str, str]] | None = None,  # (from, rel, to)
    ) -> str: ...  # returns memory_id
```

A write hits:
- Episodic (always)
- Factual (mem0) if `tier >= USER_STATED`
- Graph (FalkorDB) if `edges` provided
- Vector (Chroma/Qdrant) asynchronously, batched

---

## 5. Phased adoption — the "80/20" rollout

We don't adopt all 8 layers at once. Here's the 4-phase plan:

### Phase M0 — Inventory & name (this doc, 1 day)
- ✅ This `MEMORY_STRATEGY.md` is the contract.
- ✅ `docs/RESEARCH_LEDGER.md` is the source-of-truth for picks.
- Add a `MemoryLayer` enum to `backend/core/memory.py` and a
  `MemoryRouter` skeleton (no implementations yet — just the
  interface).

### Phase M1 — Add the two cheapest, highest-leverage layers
- **Layer: Episodic (already have it for audit, but extend)**
  - Add `episode_id`, `project`, `agent` to audit log entries
  - 1 day
- **Layer: Factual (mem0 self-hosted)**
  - `pip install mem0ai` (or `mem0` post-rename — check PyPI)
  - Run mem0 in local-only mode (Chroma backend, no external services)
  - Wire `MemoryWriter` → mem0.add() with our trust tier mapping
  - 2-3 days
- Acceptance: a CTO agent finishes a run; we can ask "what did the
  CTO learn?" and get back a list of trusted facts.

### Phase M2 — Add vector and graph
- **Layer: Vector (Chroma project-level)**
  - Embed episode summaries on write, store in project-scoped Chroma
  - 2 days
- **Layer: Graph (FalkorDB-Lite project-level)**
  - On every `reports_to` / `collaborates_with` change, write to
    FalkorDB. On every dispatch, write the (agent, agent, "messaged")
    edge.
  - 3 days
- Acceptance: the org-chart editor (from the v2 brief) reads from
  FalkorDB. "Who messaged who in the last hour?" is a 1-line query.

### Phase M3 — Add the wiki and global
- **Layer: Wiki (llm-wiki, project-level first)**
  - Use the Hermes `llm-wiki` skill, point at `state/projects/<slug>/wiki/`
  - Hand-write 5-10 starter pages: "How the War Room is organized,"
    "What each agent does," "Glossary"
  - 1 day
- **Layer: Globals (Qdrant + FalkorDB server + global mem0)**
  - `docker compose up` the globals
  - Move `user_id` from project to global for cross-project facts
  - 2 days
- Acceptance: a new project boots with a populated wiki; a fact
  learned in project A is findable from project B (but only if
  `tier=CROSS_MODEL`).

### Phase M4 (only if needed) — Letta, Hindsight, Graphiti
- **State-of-mind:** add Letta only when an agent's working context
  exceeds ~32k tokens and needs summarization.
- **Temporal:** add Graphiti only when "what was true at time T"
  queries become a real use-case.

**Do not start Phase M4 until at least 30 days of Phase M1-M3
production data.**

---

## 6. Risks and how we mitigate them

| Risk | Mitigation |
|---|---|
| **Conflicting memories** (agent A and B store opposite facts) | The `TrustTier` + `PromotionGate` from `memory.py` already handles this. USER_STATED always wins over INFERRED. |
| **Memory bloat** (100k+ facts, retrieval slows) | Half-life decay on INFERRED tier. Configurable per project. |
| **Project leakage** (project A's secrets visible in project B) | **Default-deny**: globals are opt-in, per-fact, marked `CROSS_MODEL`. `MemoryRouter` rejects cross-project recall unless explicitly requested. |
| **Vector hallucination** (semantic match returns "similar but wrong" facts) | Rerank with a small LLM (cross-encoder) before returning. Mem0 does this. |
| **Graph drift** (FalkorDB and SQLite `kanban.db` go out of sync) | Single source of truth = `kanban.db` (SQLite). FalkorDB is a *projection*. Nightly reconcile job. |
| **Mem0 abandoned / license change** | Mem0 is Apache-2.0, 58k stars, backed by a YC company. Low risk. Fallback: extract the same schema with a small in-house extractor. |
| **Tooling lock-in** | All picks are self-hostable. We can swap Chroma → Qdrant in 1 day (both speak the same vector semantics). We can swap mem0 → in-house in 1 week. |

---

## 7. Open questions for Saiyudh

1. **Where do you want the War Room's wiki to live?**
   - `state/projects/<slug>/wiki/` (project-isolated) — my default
   - `state/global/wiki/` with project sub-folders — easier to share
   - `~/wiki/` (the default `llm-wiki` location) — uses Obsidian on
     your laptop

2. **When do we add the global layer?**
   - Option A: with Phase M3 (defaults to global-from-day-one)
   - Option B: only after 2+ projects exist (avoid premature scale)
   - My default: **B** — projects first, globals once we have ≥2

3. **Do we run mem0 with a remote LLM (Anthropic/OpenAI) or local
   only (Ollama/LM Studio)?**
   - Local only: free, slower, smaller model = worse extraction
   - Remote: $0.01-0.10 per 1k facts extracted, much better
   - My default: **remote for extraction, local for retrieval** —
     the *write* path is rare and benefits from a smart model; the
     *read* path is hot and free-with-local is fine

4. **Do we want Letta/Hindsight at all?**
   - My default: **no, not yet.** Phase M1-M3 covers 80% of needs.
     Revisit after a month of real usage.

---

## 8. References

- **Full survey log:** `docs/RESEARCH_LEDGER.md` (8+ rounds, ~50
  repos surveyed, Tier-A shortlist at the bottom)
- **Decision brief for the org-chart editor that will read from
  this:** `decisions/D-2026-06-08-topology-editor.md`
- **Current memory module:** `backend/core/memory.py` (the skeleton
  we'll extend)
- **Spec section on memory:** `docs/spec.md` §3.11 (Memory DNA
  Helix) and §6.3 (Role Matrix must not mutate profile configs)
- **Hermes skill:** `llm-wiki` (Karpathy pattern, already loaded
  in this session)
- **llm-wiki skill SKILL.md:** `research/llm-wiki/SKILL.md` in the
  Hermes skills directory — defines the 3-layer wiki pattern
  (raw / wiki / schema) we should follow

