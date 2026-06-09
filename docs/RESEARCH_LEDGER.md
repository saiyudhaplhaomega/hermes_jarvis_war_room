# War Room Research Ledger

This file is the **single source of truth** for what I find, where I
found it, and how I plan to use it. Every research round appends rows
to the tables below. Each row is dated so we can tell stale findings
from fresh ones.

## How to read this

- **Tier A** = directly applicable to the War Room (War Room = our
  repo at `C:\Users\saiyu\Desktop\projects\KI_projects\hermes_jarvis_war_room`).
  Adopt / fork / copy pattern.
- **Tier B** = inspiration only. Concept is right, code isn't.
- **Tier C** = noise / trap. Worth recording so we don't re-research.

After every 2-3 rounds I'll re-rank the Tier A list and update the
Decision Brief.

---

## Round 0 — Baseline (first sweep, before this ledger existed)

| # | Repo / Source | ⭐ | What it gives us | URL | Tier | Plan |
|---|---|---|---|---|---|---|
| 0.1 | VRSEN/agency-swarm | 4.4k | Literal "agency" role pattern with communication flows | https://github.com/VRSEN/agency-swarm | A | Pattern for `jarvis_company_os` already matches this — keep as reference |
| 0.2 | openai/swarm | 21.6k | Lightweight role-handoff mental model | https://github.com/openai/swarm | A | Mental model reference for Inbox / hand-off events |
| 0.3 | microsoft/agent-framework | 11.1k | New SDK for agent workflows | https://github.com/microsoft/agent-framework | B | Worth checking for telemetry hooks |
| 0.4 | kyegomez/swarms | 6.8k | Enterprise multi-agent, role templates | https://github.com/kyegomez/swarms | B | Lots of role-template examples to crib from |
| 0.5 | crewAI | 30k+ | Most popular role+task framework | https://github.com/crewAIInc/crewAI | A | Reference for Issues/Task model (we don't have it) |
| 0.6 | iriseye931-ai/mission-control-dashboard | 11 | React + WS real-time mesh view of agents | https://github.com/iriseye931-ai/mission-control-dashboard | A | Direct inspiration for the 3D bridge |
| 0.7 | opsrobot-ai/opsrobot | 137 | Observability for "Digital Employee" | https://github.com/opsrobot-ai/opsrobot | A | Cost/trace patterns |
| 0.8 | tannht/claude-code-monitoring-dashboard | 2 | Next.js 15 + SQLite for Claude swarms | https://github.com/tannht/claude-code-monitoring-dashboard | A | Reference for our SQLite schema |
| 0.9 | honorstudio/claude-ville | 12 | Isometric pixel world of Claude Code agents | https://github.com/honorstudio/claude-ville | B | UI inspiration for the cinematic panel |
| 0.10 | Thrilok28021996/multi-agent-llm-company-system | 0 | Software-company sim on local Ollama LLMs | https://github.com/Thrilok28021996/multi-agent-llm-company-system | C | Niche |
| 0.11 | Zeeshanmuqaddas/AUTONOMOUS-AI-COMPANY-ORCHESTRATOR- | 1 | CEO/CTO/CMO/CFO with Gemini 2.5 | https://github.com/Zeeshanmuqaddas/AUTONOMOUS-AI-COMPANY-ORCHESTRATOR- | C | Niche |
| 0.12 | ogtayhuseynov0/claude-wall | — | Mission control for many Claude sessions | https://github.com/ogtayhuseynov0/claude-wall | B | UI inspiration |
| 0.13 | Kocoro-lab/Shannon | 2.0k | Production-oriented agent flows | https://github.com/Kocoro-lab/Shannon | B | Reliability patterns |

## Round 1 — Broad GitHub sweep, niche AI-org repos

| # | Repo / Source | ⭐ | What it gives us | URL | Tier | Plan |
|---|---|---|---|---|---|---|
| 1.1 | **Spectral-Finance/lux** | 113 | "Swarmed intelligence" framework with Beams, Prisms, Lenses (multi-agent roles) | https://github.com/Spectral-Finance/lux | A | Borrow the "Prism/Lens" naming for our agent types |
| 1.2 | **xvirobotics/metabot** | 856 | Supervised, self-improving AI org infrastructure. Feishu/Telegram interface. **Very on-target.** | https://github.com/xvirobotics/metabot | A | Study the "supervisor over self-improving org" pattern — solves the same problem as our wake/hiring cycle |
| 1.3 | **xuiltul/animaworks** | 238 | Brain-inspired memory system (consolidation, forgetting) for multi-model Claude/Codex/Gemini agents | https://github.com/xuiltul/animaworks | A | Their memory model is more sophisticated than ours — borrow for Memory Nexus V2 |
| 1.4 | **JustinAngelson/CentralMemoryHub** | 11 | Vendor-neutral shared memory with MCP + REST, designed for multi-agent systems | https://github.com/JustinAngelson/CentralMemoryHub | A | MCP-compatible shared memory is the future — we should plan for MCP |
| 1.5 | anote-ai/Autonomous-Intelligence | — | Collaborative intelligent systems framework | https://github.com/anote-ai/Autonomous-Intelligence | B | Generic reference |
| 1.6 | **strnad/CrewAI-Studio** | 1,290 | Streamlit GUI for managing crewAI agents/tasks | https://github.com/strnad/CrewAI-Studio | A | **Major inspiration for our "Mission Control" UX**. Take screenshots of their workflow and steal patterns |
| 1.7 | shaozheng0503/aimv-studio | 9 | MV director: 4 specialized agents (screenwriter/director/music/verifier) | https://github.com/shaozheng0503/aimv-studio | B | 4-agent specialty pattern matches our domain leads |
| 1.8 | AISquare-Studio/AISquare-Studio-QA | 166 | QA testing agents with playwright | https://github.com/AISquare-Studio/AISquare-Studio-QA | B | Domain: testing. Reference for our QA lead |
| 1.9 | ezeeFlop/SpongeAgentStudio | 4 | Generic agent studio | https://github.com/ezeeFlop/SpongeAgentStudio | C | Niche |

## Round 2 — 2D editable org chart / graph editor libraries (React)

| # | Repo / Source | ⭐ | License | What it gives us | URL | Tier | Plan |
|---|---|---|---|---|---|---|---|
| 2.1 | **xyflow/xyflow** (was reactflow) | 37k | MIT | The de-facto React node/edge library. Active, well-maintained. Now `@xyflow/react`. | https://github.com/xyflow/xyflow | A | **Use it.** v12 is current. Pair with dagre for layout |
| 2.2 | **dagrejs/dagre** | 5.7k | MIT | Directed graph auto-layout (rank-based, edge-crossing-minimizing) | https://github.com/dagrejs/dagre | A | Use for initial org-chart layout. Now in TypeScript |
| 2.3 | **elkjs/elk** (Eclipse Layout Kernel) | 5k+ | EPL-2.0 | More advanced layered layout (the "industry" choice) | https://github.com/kieler/elkjs | A | Backup if dagre isn't good enough. License is copyleft, MIT preferred |
| 2.4 | randomdrake/react-flow-org-chart | 6 | MIT | Proof-of-concept org chart using React Flow | https://github.com/randomdrake/react-flow-org-chart | A | Use as a starting template |
| 2.5 | alex-laycalvert/react-flow-orgchart | 0 | MIT | Clean example org chart with React Flow | https://github.com/alex-laycalvert/react-flow-orgchart | A | Code reference for custom node rendering |
| 2.6 | **halmadany/org-visualizer** | 0 | MIT | Org visualization with React Flow + Zustand | https://github.com/halmadany/org-visualizer | A | **Adopt their Zustand pattern** for the editor state |
| 2.7 | otomamaYuY/organo-core | 0 | ? | Interactive org chart editor with React Flow | https://github.com/otomamaYuY/organo-core | A | Reference for editing affordances |
| 2.8 | msshaffer35/org-chart-app | 0 | MIT | Modern org chart with Vite + React Flow | https://github.com/msshaffer35/org-chart-app | A | Vite + RF config we can copy |

## Round 3 — Visual agent / flow builder dashboards (drag-and-drop)

| # | Repo / Source | ⭐ | What it gives us | URL | Tier | Plan |
|---|---|---|---|---|---|---|
| 3.1 | **langflow-ai/langflow** | 149k | The de-facto drag-and-drop LLM/agent builder. FastAPI + React. | https://github.com/langflow-ai/langflow | A | **Major inspiration** for our topology editor UX. Use their "drag component, drop on canvas" pattern |
| 3.2 | **FlowiseAI/Flowise** | 53.4k | "Build AI Agents, Visually." LangChain-based, similar pattern to Langflow. | https://github.com/FlowiseAI/Flowise | A | Take their Canvas node-rendering patterns. Use their docs/tutorials as a UX benchmark |
| 3.3 | **proinsight-io/crewmeld** | 56 | Enterprise AI Digital Workforce: Visual SOP orchestration, 13 LLM providers, 8 messaging channels | https://github.com/proinsight-io/crewmeld | A | **Direct competitor** — borrow their "AI employees like real team members" framing and their Next.js + React + TS + Bun monorepo structure |
| 3.4 | shamspias/langgraph-agent-system | 14 | Production-ready multi-agent with LangGraph, specialized agents, multi-provider LLM | https://github.com/shamspias/langgraph-agent-system | A | Reference for "specialized agents" pattern, multi-LLM provider strategy |
| 3.5 | **Muhammad-Hassan12/AgenticEra-Studio** | 2 | Supervisor orchestrator + Research/Task Planner/Document Analyst agents. FastAPI + Next.js + TS | https://github.com/Muhammad-Hassan12/AgenticEra-Studio | A | **Adopt the "supervisor + 3 specialists" pattern** for our Boss + CTO/CMO/Research arrangement |
| 3.6 | shakehasan/multi-agent-research-studio | ? | Local-first, MCP, LlamaIndex, vector stores, eval, Docker, Temporal, Next.js | https://github.com/shakehasan/multi-agent-research-studio | A | Confirms local-first + MCP is the modern stack — align with this |
| 3.7 | kingdoja/content-creator-studio | 0 | LangGraph + FastAPI + long-term memory + RAG + streaming workflows | https://github.com/kingdoja/content-creator-studio | A | Reference for streaming workflow UX in our War Room |
| 3.8 | Bilal0080/Digital-FTE-Autonomous-AI-Employee | 0 | "Digital FTE Factory" command center for AI employees | https://github.com/Bilal0080/Digital-FTE-Autonomous-AI-Employee | C | Marketed well but generic |
| 3.9 | anisabidd88-pro/ai-workforce-digital-twin | 1 | Multi-agent sim with RL optimization, real-time analytics | https://github.com/anisabidd88-pro/ai-workforce-digital-twin | B | Their analytics dashboard is a reference |
| 3.10 | dandyz1115/WanGe-AIGC-Digital-Employee | 0 | WanGe AIGC Mgmt System, deployed on Vercel | https://github.com/dandyz1115/WanGe-AIGC-Digital-Employee | C | Deployed demo for design reference |

## Round 4 — LLM observability & tracing platforms

| # | Repo / Source | ⭐ | License | What it gives us | URL | Tier | Plan |
|---|---|---|---|---|---|---|---|
| 4.1 | **langfuse/langfuse** | 28.7k | MIT (some EE Apache) | OpenTelemetry-native LLM observability. Tracing, metrics, evals, prompt mgmt, playground | https://github.com/langfuse/langfuse | A | **Borrow the OTEL trace schema** for our army.py events. Their session/trace UI is the standard to beat |
| 4.2 | **openlit/openlit** | 2.5k | Apache-2.0 | OTEL-native, GPU monitoring, 50+ LLM providers, vector DB, agent framework support | https://github.com/openlit/openlit | A | Worth a look if we want zero-code instrumentation. Langfuse is still the lead |
| 4.3 | **traceloop/openllmetry** | — | Apache-2.0 | OTEL-instrumentation libraries for Python, JS, Go | https://github.com/traceloop/openllmetry | A | Use their OTEL SDK wiring pattern for our backend |
| 4.4 | **pydantic/pydantic-ai** | 17.6k | MIT | "AI Agent Framework, the Pydantic way" — fast growing, modern | https://github.com/pydantic/pydantic-ai | A | Use their typed-IO + tool validation patterns; their `clai` CLI shows the dashboard direction |

## Round 5 — 3D org chart / cinematic command-deck libraries (subagent-verified)

| # | Repo / Source | ⭐ | License | What it gives us | URL | Tier | Plan |
|---|---|---|---|---|---|---|---|
| 5.1 | **vasturiano/react-force-graph** | 3.2k | MIT | 2D/3D/VR/AR force-directed graph React component | https://github.com/vasturiano/react-force-graph | A | **The de-facto React 3D network graph.** Drop-in for our constellation panel |
| 5.2 | **vasturiano/r3f-forcegraph** | 46 | MIT | Same data, but as a React Three Fiber component | https://github.com/vasturiano/r3f-forcegraph | A | Use this for the 3D Command Deck — full Three.js control over nodes/edges |
| 5.3 | **Gaurav2693/ai-office** | 35 | MIT | Miniature isometric 3D office: 9 AI agents working/walking/talking/meeting. React 19 + Three.js | https://github.com/Gaurav2693/ai-office | A | **1:1 match for the spec**. Blueprint for our cinematic "office" panel |
| 5.4 | **IvanWng97/pixtuoid** | 235 | MIT | Terminal pixel-art office for AI coding agents | https://github.com/IvanWng97/pixtuoid | A | Most-starred agent-office project; battle-tested sprite-grid pattern |
| 5.5 | **ruiqili2/agent-monitor** | 55 | MIT | Real-time agent viz in pixel office (Claude CLI / Codex) | https://github.com/ruiqili2/agent-monitor | A | Copy data-binding / event-stream patterns for army ops |
| 5.6 | **rolandal/pixel-agents-standalone** | 46 | MIT | Standalone web app: Claude Code sessions as pixel-art characters in virtual office | https://github.com/rolandal/pixel-agents-standalone | A | Clean dependency-light "agents as characters" reference |
| 5.7 | **thx0701/openclaw-virtual-office** | 45 | MIT | Virtual office for OpenClaw agents — pixel art | https://github.com/thx0701/openclaw-virtual-office | A | Compare state-machine designs |
| 5.8 | **W17ant/Claude-Office** | 30 | MIT | Pixel-art virtual office for AI agents, real-time, Claude Code hooks, WebSocket events | https://github.com/W17ant/Claude-Office | A | Real-time WS-driven event model — direct fit for mission control |
| 5.9 | **askmojo/moltcraft** | 31 | ? | "Your AI Agents, Alive in a World" — isometric dashboard for Moltbot | https://github.com/askmojo/moltcraft | B | Mood-board for "alive world" aesthetic |
| 5.10 | **JacksonHe04/multi-agent-system** | 2 | ? | Multi-agent viz platform using React Force Graph + A-Frame | https://github.com/JacksonHe04/multi-agent-system | B | Thematic alignment: literal multi-agent 3D viz |
| 5.11 | **jexp/neo4j-3d-force-graph** | small | MIT | Neo4j + 3d-force-graph | https://github.com/jexp/neo4j-3d-force-graph | B | Reference for wiring graph DB into 3D view |
| 5.12 | **mohidmakhdoomi/nextjs-3d-force-graph-impl** | 6 | MIT | Next.js App Router + 3D force graph, Vercel-deployed | https://github.com/mohidmakhdoomi/nextjs-3d-force-graph-impl | A | Next.js + 3D scaffold |

## Round 6 — Animation libraries for graph/org-chart transitions (subagent-verified)

| # | Repo / Source | ⭐ | License | What it gives us | URL | Tier | Plan |
|---|---|---|---|---|---|---|---|
| 6.1 | **framer/motion** (the de-facto React animation lib) | n/a | MIT | Spring animations, `layoutId` shared transitions, drag physics | https://github.com/framer/motion | A | Use `layoutId` for handoff animations between panels |
| 6.2 | **CubeStar1/dsa-visualizer** | 26 | MIT | React Flow + Framer Motion + Next.js | https://github.com/CubeStar1/dsa-visualizer | A | Production example of animated React Flow nodes — copy node-position/spring-config |
| 6.3 | **ayanasamuel8/Aether** | new | ? | Go (Clean Architecture) + React Flow + Framer Motion, AI-driven roadmap decomposition | https://github.com/ayanasamuel8/Aether | B | Most architecturally rich Framer-Motion + React-Flow project |
| 6.4 | **TaewoooPark/NODEPROMPT** | 41 | ? | 3D concept graphs with spatial prompt engineering | https://github.com/TaewoooPark/NODEPROMPT | B | Bridges 3D graph + node animation |
| 6.5 | **Louis3797/wikipedia-graph** | 37 | MIT | R3F + TS graph project | https://github.com/Louis3797/wikipedia-graph | A | Camera-flythrough / focus-pull animation reference |
| 6.6 | **cx-shay-shimonov/Animate-ReactFlow-Nodes** | 0 | MIT | Minimal reference for animating React Flow node position transitions | https://github.com/cx-shay-shimonov/Animate-ReactFlow-Nodes | A | **Exactly the technique we need** for kanban/role handoff animations |

## Round 7 — Major direct hits (final pass — high-value references)

| # | Repo / Source | ⭐ | License | What it gives us | URL | Tier | Plan |
|---|---|---|---|---|---|---|---|
| 7.1 | **crewAIInc/crewAI** | 53.1k | MIT | The most popular role-playing, autonomous agent framework. Crews + Tasks + Flows | https://github.com/crewAIInc/crewAI | A | **Reference for "Issues/Task" model** (our spec calls Issues the coordination primitive — we don't have one). Borrow their `Flow` runtime |
| 7.2 | **browser-use/browser-use** | 97.7k | MIT | Make websites accessible to AI agents | https://github.com/browser-use/browser-use | B | Adjacent but big — their SDK architecture is a reference |
| 7.3 | **humanlayer/humanlayer** | 11k | MIT | "The best way to get AI coding agents to solve hard problems." Daemon (`hld/`) + CLI (`hlyr/`) + Web UI (`humanlayer-wui/`) | https://github.com/humanlayer/humanlayer | A | **Direct reference for our Inbox + HITL approval flow.** Their `hld` → `hlyr` → `wui` split maps perfectly to our backend → CLI → React UI |
| 7.4 | **pydantic/pydantic-ai** | 17.6k | MIT | Pydantic-style typed agent framework. Growing fast. | https://github.com/pydantic/pydantic-ai | A | Use their typed IO + tool validation in our army workers |

## Round 8 — LLM cost / token accounting dashboards

| # | Repo / Source | ⭐ | License | What it gives us | URL | Tier | Plan |
|---|---|---|---|---|---|---|---|
| 8.1 | **JingbiaoMei/Tokdash** | 16 | MIT | Beautiful visualization + analytics for LLM API consumption | https://github.com/JingbiaoMei/Tokdash | A | Use as a reference for per-model / per-day / per-agent cost charts |
| 8.2 | **iamgeetarted/tokenwatch** | 0 | MIT | Token tracking/monitoring + AI optimization advisor, live Rich TUI | https://github.com/iamgeetarted/tokenwatch | B | TUI patterns are good for our terminal panel |
| 8.3 | **ZSeven-W/local-llm-router** | 1 | MIT | Local AI routing gateway with cost tracking, proxies OpenAI/Anthropic/Ollama/LM Studio | https://github.com/ZSeven-W/local-llm-router | A | **Direct match for our hybrid local+cloud LLM goal** |
| 8.4 | **bhagyashreewagh/llmaven-dashboard** | 0 | MIT | Spend analytics for LiteLLM proxy logs: cost, latency, cache efficiency, sessions | https://github.com/bhagyashreewagh/llmaven-dashboard | A | Use their LiteLLM log-parsing pattern; LiteLLM is a great aggregation layer |
| 8.5 | **roloport/tokenpulse** | n/a | ? | "Mission control" for LLM developers — track, audit, optimize | https://github.com/roloport/tokenpulse | B | Their name says it all |

---

## Tier-A "Adopt Now" Shortlist (after 8+ rounds of research)

These are the highest-value references for the **War Room** specifically. Listed in
the order we'd adopt them.

1. **xyflow/xyflow** (37k, MIT) — the editor library. 2D editable org chart with React Flow + dagre. **Round 2**
2. **vasturiano/react-force-graph** (3.2k, MIT) + **vasturiano/r3f-forcegraph** (46, MIT) — 2D/3D force-directed graph for the constellation + command deck. **Round 5**
3. **framer/motion** + **CubeStar1/dsa-visualizer** + **cx-shay-shimonov/Animate-ReactFlow-Nodes** — for handoff animations between roles. **Round 6**
4. **Gaurav2693/ai-office** (35, MIT) — blueprint for the 3D isometric office. **Round 5**
5. **langfuse/langfuse** (28.7k, MIT) — OTEL trace schema for our `army.py` events. **Round 4**
6. **humanlayer/humanlayer** (11k, MIT) — `hld` daemon + `hlyr` CLI + `wui` web UI architecture for HITL. **Round 7**
7. **crewAIInc/crewAI** (53.1k, MIT) — the "Issues are the coordination primitive" model. **Round 7**
8. **langflow-ai/langflow** (149k) + **FlowiseAI/Flowise** (53.4k) — drag-and-drop visual reference for our topology editor. **Round 3**
9. **proinsight-io/crewmeld** (56) — direct competitor; their monorepo structure + "AI employees like real team members" framing. **Round 3**
10. **xvirobotics/metabot** (856) — supervisor over self-improving AI org. Closest philosophical match. **Round 1**

---

## Round M1 — Memory systems (the 8 kinds, free + self-hosted)
| # | Repo / Source | ⭐ | License | What it gives us | URL | Tier | Plan |
|---|---|---|---|---|---|---|---|
| M1.1 | **mem0ai/mem0** (v3, April 2026) | 58.1k | Apache-2.0 | "Universal memory layer." v3 algorithm SOTA: 91.6 LoCoMo / 94.8 LongMemEval / 64.1 BEAM-1M. Single-pass ADD-only extraction (no UPDATE/DELETE). Multi-signal retrieval: semantic + BM25 + entity, fused. Temporal reasoning. Default LLM `gpt-5-mini`. Default embedder `text-embedding-3-small` (or Qwen 600M for hybrid). Plugins: Claude, Codex, OpenCode, Cursor, Windsurf, OpenClaw, Vercel AI SDK. Has `mem0` CLI, `mem0-integrate` skill, `mem0-test-integration` skill. Self-hosted via `cd server && make bootstrap` | https://github.com/mem0ai/mem0 | A | **Co-primary pick for §1.4 with Hindsight.** Use mem0 v3 for project-level facts, Hindsight for state-of-mind/learning. **The v3 algorithm specifically** (single-pass ADD-only) maps to our `OBSERVED/USER_STATED/INFERRED` tier system — observed facts are ADD-only, no overwrite |
| M1.2 | **vectorize-io/hindsight** | 16k | MIT | "Agent Memory That Learns." 3 pathways (World/Experience/Mental-Model), 3 ops (retain/recall/reflect), 4 parallel retrieval strategies (semantic/keyword/graph/temporal), supports `ollama`/`lmstudio`/`minimax`/`anthropic`/`openai`/`gemini`/`groq` as LLM providers. SOTA on LongMemEval (Jan 2026). Verified by Virginia Tech + WaPo. Production at Fortune 500. Has paper arxiv:2512.12818. Embedded mode: `pip install hindsight-all`. Server mode: docker run on :8888 (API) + :9999 (UI) | https://github.com/vectorize-io/hindsight | A | **Adopt now (per user direction).** Wire into the project-level memory bank. The `retain/recall/reflect` API replaces the simpler `add/search` of mem0 and is purpose-built for *learning*, not just storing. **This is a primary pick for the War Room's project-level memory.** |
| M1.3 | **getzep/graphiti** | 27.2k | Apache-2.0 | "Temporal Context Graphs for AI Agents." **Facts have temporal validity windows** (valid_from, valid_until — old facts invalidated not deleted). Entities + facts + episodes (raw provenance). Hybrid retrieval: semantic + BM25 + graph traversal, **no LLM at query time**. Has **MCP server** (mcp_server/) — Claude/Cursor can talk to it natively. Pluggable backends: Neo4j, FalkorDB. Paper arxiv:2501.13956 | https://github.com/getzep/graphiti | A | **Adopt for §1.8 (temporal relationships).** Critical for War Room: "what model was the eng-lead using when we deployed v1.4?" queries. Use as the project-level "who knows what and when" store. Wire via MCP so any agent can query it |
| M1.4 | **letta-ai/letta** (formerly MemGPT) | 23.2k | MIT | Stateful agents with **memory blocks** (label/value pairs: human, persona, custom). `@letta-ai/letta-code` CLI for terminal agents. **Skills + subagents** pattern. **Continual learning**. Model-agnostic (recommends Opus 4.5, GPT-5.2). Paper: MemGPT | https://github.com/letta-ai/letta | A | **Adopt for §1.7 (state-of-mind) when needed.** Use for individual agents that need a rolling scratchpad. Skip for v1; revisit when an agent loop exceeds ~32k tokens |
| M1.5 | **topoteretes/cognee** | 17.7k | Apache-2.0 | "AI memory platform for agents." ECL pipeline (extract, cognify, load). Vector + graph + ontology in one tool. **Has Claude Code plugin + OpenClaw plugin.** Paper arxiv:2505.24478 | https://github.com/topoteretes/cognee | A | **All-in-one alternative.** If we want one tool for §1.2+§1.3+§1.4, pick cognee. If we want best-of-breed, stick with mem0 + Chroma + FalkorDB |
| M1.6 | **FalkorDB/FalkorDB** | 4.5k | **SSPLv1** (NOT OSI-approved!) | "Ultra-fast Graph Database." Sparse matrix for adjacency. OpenCypher compatible. **Multi-tenant.** Docker: `docker run -p 6379:6379 -p 3000:3000` | https://github.com/FalkorDB/FalkorDB | A (with caveat) | **Default for §1.3 (graph)** but **read the license.** SSPL blocks SaaS redistribution. Fine for self-hosted War Room. Watch for **license trap** if we ever ship a hosted version |
| M1.7 | **chroma-core/chroma** | ~17k | Apache-2.0 | "Open-source data infrastructure for AI." Embedded mode (`pip install chromadb`) and client-server mode (`chroma run --path ...`). Hybrid + full-text + vector. Chroma Cloud with $5 free credits. Embedded = single Python import, zero ops | https://github.com/chroma-core/chroma | A | **Default for §1.2 (vector) project-level.** Zero ops, Python-native. If we outgrow it, swap to Qdrant |
| M1.8 | **qdrant/qdrant** | ~24k | Apache-2.0 | "Vector Search Engine for next-gen AI." Rust, fast, production-grade. Free Cloud tier. Filtering + payload support. Best for >1M vectors | https://github.com/qdrant/qdrant | A | **Default for §1.2 (vector) global-level.** When project-level memory scales up to cross-project, point all collections at a single Qdrant cluster |
| M1.8b | **lance-format/lance** + lancedb | ~4k+ | Apache-2.0 | "Open Lakehouse Format for Multimodal AI." Columnar, Pandas/Polars/DuckDB/PyArrow compatible. Embedded (lancedb) or distributed (Spark/Ray) | https://github.com/lance-format/lance | B | **Watch this one.** Best when we want to mix vectors with tabular metadata at scale. Not for v1 |
| M1.9 | **karpathy/llm-wiki** | n/a (gist) | n/a (CC-BY-SA gist) | Karpathy's LLM Wiki pattern. Interlinked markdown KB with raw/wiki/schema 3 layers | https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f | A | **Default for §1.5 (wiki).** Already loaded as a Hermes skill in this session |
| M1.10 | **JustinAngelson/CentralMemoryHub** | 11 | MIT | Vendor-neutral shared memory, MCP + REST | https://github.com/JustinAngelson/CentralMemoryHub | B | MCP-compatible shared memory; alternative pattern |
| M1.11 | **xuiltul/animaworks** | 238 | MIT | Brain-inspired memory: consolidation + forgetting. Multi-model (Claude/Codex/Gemini) | https://github.com/xuiltul/animaworks | A | Reference for "consolidation, forgetting" subroutines in our `ConfidenceDecay` |

## Round M2 — Brain-inspired memory theory + half-life decay

Sources surveyed:
- **animaworks** (above) — consolidation, forgetting, multi-model
- **gstack Memory v0** (already in our repo at `backend/core/memory.py`!) — `OBSERVED/USER_STATED/INFERRED/CROSS_MODEL` tiers + half-life decay + promotion gate
- **Letta paper (MemGPT)** — core/archival/recall hierarchy

**Key insight:** we already have the *theory* in `memory.py`. What's missing is the *storage* and *retrieval* — that's what M1.x picks fill in.

## Round M3 — Knowledge graph backends

| # | Repo / Source | ⭐ | License | What it gives us | URL | Tier | Plan |
|---|---|---|---|---|---|---|---|
| M3.1 | **FalkorDB/FalkorDB** | 4.5k | BSD-3 | Already counted in M1.6. Embedded Lite version | (above) | A | Default |
| M3.2 | kuzudb/kuzu | 3.5k+ | MIT | Embedded graph DB (C++). Cognee used to use it, switched to Ladybug | https://github.com/kuzudb/kuzu | B | Alternative to FalkorDB-Lite |
| M3.3 | neo4j/neo4j | 13k+ | GPL-3.0 (community) | The OG graph DB. Heavy | https://github.com/neo4j/neo4j | C | License + ops cost. Skip |
| M3.4 | memgraph/memgraph | 2.5k+ | BSL | In-memory graph. C++/Cython | https://github.com/memgraph/memgraph | B | Alternative to FalkorDB |





---

# LOOP 2 — MiroFish-style Research / Growth Agents

## Round 1 — MiroFish-Offline architecture ✅
- **Repo:** `nikmcfly/MiroFish-Offline` (cloned). Original: `666ghj/MiroFish`
- **License:** AGPL-3.0 (⚠️ copyleft — adopt the *pattern*, not the code)
- **5-stage pipeline:** Graph Build → Env Setup (personas) → Simulation → Report → Interaction
- **Stack:** Neo4j 5.15 Community + Ollama (qwen2.5) + nomic-embed-text. 100% local.
- **Key innovation:** ReportAgent **interviews a focus group of personas + queries the knowledge graph** to produce a structured analysis. Each persona has memory + personality.
- **Council verdict (codex + qwen2.5:3b):** **ADAPT, not adopt.** Our agents are persistent named identities (13+), not 100s of disposable personas. Borrow the 5-stage *structure* (intake → context graph → agent briefing → simulation/council → report → chat/actions), skip "persona generation" as a core stage.
- **What to steal:** the **ReportAgent pattern** (one agent interviews the focus group + queries graph) — perfect for our **scout** + **council** pair
- **What to skip:** persona generation (we have bosses/managers/leads), Chinese-cloud integrations


## Round 2 — STORM (Stanford, knowledge curation) ✅
- **Repo:** `stanford-oval/storm` (MIT), pip `knowledge-storm` v1.1.0
- **Innovation:** **Perspective-Guided Question Asking** — for any topic, LLM discovers multiple perspectives (operator, customer, competitor, regulator, etc.) and asks targeted questions from each lens
- **Co-STORM** (Sept 2024): human + LLM collaborative discourse protocol
- **Council verdict (codex):** **Adopt selectively.** Implement as an optional `perspective_guided=true` research mode in War Room. Use for: strategy, market research, policy, technical tradeoffs, risk assessment. Skip for: simple fact lookup.
- **Output format tweak:** instead of Wikipedia articles, output **briefs, claims, evidence tables, unknowns, recommendations, next actions** — fits War Room's decision-support purpose
- **Citation integration:** STORM uses Bing search. War Room can use it to enrich our **scout** agent's web research phase


## Round 3 — GPT-Researcher ✅
- **Repo:** `assafelovic/gpt-researcher` (MIT), pip `gpt-researcher`, has Claude Skill `npx skills add assafelovic/gpt-researcher`
- **Pattern:** Plan-and-Solve + RAG, parallelized research, deep report generation with citations
- **Council verdict (codex):** **Use as a specialist tool, NOT as org architecture.** 
  - Weaker than STORM for adversarial breadth (one research plan, not multi-perspective)
  - Too transient for 13+ persistent agents (run-once, write report)
  - **Best role:** back the `scout` or `researcher` agent with it. War Room orchestrator stays in charge.


## Round 4 — DeerFlow (ByteDance) ✅
- **Repo:** `bytedance/deer-flow` v2.0 (MIT, Python 3.12+ + Node 22+). #1 GitHub trending Feb 2026.
- **Pattern:** "Super agent harness" orchestrating sub-agents + memory + sandboxes via **extensible skills**
- **Roles:** Planner / Researcher / Coder / Reporter + human-in-the-loop
- **Council verdict (codex):** **Adopt the role split as a sub-pattern within existing agents.** Don't copy wholesale. Best fit: Planner=mission decomposition, Researcher=intel/sources, Coder/Operator=tool exec, Reporter=briefs/logs. **Human-in-the-loop is essential** at decision gates (high-cost, external publishing, destructive changes).


## Round 5 — Open Deep Research (HuggingFace smolagents) ✅
- **Repo:** `huggingface/smolagents` (Apache-2.0). Single **CodeAgent** that writes Python to do research with tools.
- **Council verdict (codex):** **Start with single CodeAgent for execution, wrap in DeerFlow-like role layer at product level** (planner queue, researcher runs, verifier/reviewer, reporter output). Keeps implementation lean while preserving War Room's command-center structure.
- **Tradeoff logged:** smolagents = easy to inspect, but single agent can drift/mix concerns. DeerFlow = cleaner separation + checkpoints, but more coordination overhead.


## Round 6 — AI-CoScientist (The-Swarm-Corporation) ✅
- **Repo:** `The-Swarm-Corporation/AI-CoScientist` (cloned, MIT)
- **Pattern:** 8-agent pipeline (Generation → Reflection → Ranking → Evolution → Meta-review → Proximity → Supervisor → Conversation Manager)
- **Key innovation:** **Elo-style tournament ranking** of hypotheses via pairwise comparisons
- **Workflow:** 8 phases, iterative refinement with diversity control
- **Council verdict (codex):** **Use as research triage engine.** Generate hypotheses, attack weak ones, surface top, route to humans/tools for validation. **Don't trust Elo alone** — needs evidence, novelty, feasibility, falsifiability scoring. **Guardrail:** audit logs + citations + experiment tracking + human approval before direction changes.
- **Fits War Room's:** `scout` (generation) + `council` (meta-review) + `qa-lead` (attack) trio


## Round 7 — Agentic RAG patterns ✅
- **Council verdict (codex):** **Adopt agentic RAG for high-value analytical workflows**, keep traditional single-pass for simple lookups.
- **Must-have patterns:**
  - **Query rewriting** — rephrase the user's question into better retrieval queries
  - **Iterative retrieval** — retrieve → inspect gaps → retrieve again when evidence weak
  - **Self-correction** — verify the answer is supported by retrieved evidence, flag uncertainty, retry
  - **Multi-hop reasoning** — chained retrieval for "which incident caused this KPI drop and what policy changed?"
- **Maps to War Room:** `scout` agent handles retrieval + rewriting; `qa-lead` or `council` handles self-correction step


## Round 8 — Knowledge graph auto-population ✅
- **Council verdict (codex):** **Hybrid extraction** is best default.
  - **Rules/OpenIE** for: IDs, timestamps, mentions, task refs, file paths, links, known relation templates — fast + deterministic
  - **LLM** for: semantic relation extraction, summarizing evidence, resolving ambiguity, mapping to project ontology
- **War Room ontology** (validated facts only): `Agent, Task, Decision, Artifact, Dependency, Risk, Requirement, Claim, Source, Owner, Status`
- **Cadence:** **Real-time lightweight ingestion** for mentions/links/decisions/handoffs + **batched LLM consolidation** every few minutes (or at conversation/doc boundaries)
- **Storage pattern:** project-level graph + per-agent event streams. Every chat/doc/action = immutable evidence, then promote to graph


## Round 9 — Continuous-learning loops ✅
- **Council verdict (codex):** **In-context memory accumulation is primary** (per-run updates via mem0/Hindsight). Prompt evolution + fine-tuning are secondary.
- **Cadence recommendations:**
  - **Every run:** memory updates (mem0 retain / Hindsight retain)
  - **Daily/weekly:** memory pruning + summarization (decay old facts)
  - **Weekly:** prompt review with **meta-prompts proposing improvements, gated by evaluation suite before promotion** (treat prompts as versioned config, not live self-modifying behavior)
  - **Monthly/quarterly:** fine-tuning, only for stable repeated behaviors (house style, tool discipline, domain triage), after 50-200 validated examples + regression eval suite passes


## Round 10 — The "knowledge garden" pattern (curation + pruning) ✅
- **Council verdict (codex):** Knowledge should **GROW + GET PRUNED**, not just accumulate.
- **Lifecycle:** `active → dormant → archived → delete candidate`
- **What to auto-prune:** duplicates, superseded facts (with replacement), unreferenced items > N days
- **What to human-archive:** decisions, postmortems, key evidence, customer/user quotes, irreversible tradeoffs, anything tied to compliance/trust/strategy
- **Promote/demote by use:** promote when reused/cited/confirmed/attached to active decisions; demote when unreferenced/contradicted/historically useful only
- **Prefer decay before hard delete** — hard delete only for: junk, duplicates, sensitive data, explicitly-approved removal
- **Make pruning explainable:** every action shows timestamp + rule triggered + confidence + recovery path. e.g. "Demoted because unused for 45 days and superseded by Decision #18."


---

# LOOP 3 — LLM Council + Multi-Model Orchestration

## Round 1 — karpathy/llm-council ✅
- **Repo:** `karpathy/llm-council` (vibe-coded, MIT/CC). Uses OpenRouter.
- **3-stage pattern:** Stage 1 parallel answers → Stage 2 anonymized ranking → Stage 3 chairman synthesis
- **Council verdict (codex):** **Adopt for strategic decisions only** (architecture, security, research synthesis, ambiguous plans). Skip for routine execution.
- **Critical refinements:**
  - Stage 2 must rank by **criteria** (correctness, risk, completeness, actionability) — not vague "best answer"
  - Stage 3 chairman must **preserve minority warnings** instead of blind-averaging
  - Anonymization is essential in Stage 2 (prevent "favor the prestigious model" bias)


## Round 2 — AgentVerse / MetaGPT / ChatDev / AutoGen ✅
- **Council verdict (codex):** **Borrow from AgentVerse + MetaGPT primarily.**
  - **AgentVerse** — 13+ agent hierarchy + routing (perfect for our existing org)
  - **MetaGPT** — SOPs, document handoffs, role-to-deliverable discipline (PM/architect/eng/QA producing structured artifacts)
  - **AutoGen (selective)** — group chat pattern, speaker selection, tool-using, nested conversations for debate/escalation
  - **ChatDev (selective)** — phase-based execution + review gates for predictable build/review cycles
- **Concrete borrowing list:**
  - From MetaGPT: **structured output schemas** for each role (Manager → plan, Eng-lead → spec, QA → test plan, Docs → markdown)
  - From AgentVerse: **role registration** with capabilities + availability + budget
  - From AutoGen: **group chat with human-in-the-loop speaker selection**
  - From ChatDev: **phase gates** (no eng code without QA sign-off, no docs without code, etc.)


## Round 3 — Multi-model debate: who judges? ✅
- **Council verdict (codex):** **Third-party judge by default** (a model not in the debate). Escalate to human when: confidence low OR stakes high OR models strongly disagree.
- **Why not designated judge:** creates single-model bias + single point of failure
- **Why not self-judge:** ego/anchoring too high
- **Why not human-only:** slow + expensive + inconsistent at scale (use only for high-stakes escalation)
- **Maps to War Room:** our `council` agent plays third-party judge for routine decisions; `boss` escalates to you (Saiyudh) when confidence < threshold or stakes cross budget/audit gates


## Round 4 — Confidence scoring across models ✅
- **Council verdict (codex):** **Sample 2-3 times, extract key claim, compare for agreement.** Don't trust logprobs alone (high confidence ≠ truth — hallucinations can be confident).
- **Decision matrix:**
  - **Same answer (multi-sample):** probably safe to proceed
  - **Conflicting answer:** needs evidence grounding or human review
  - **No answer:** model lacks knowledge; route to scout or external source
  - **Unanimous agreement:** still **not proof of truth** — must ground against sources/tools/known data
- **Cost:** ~3× the LLM calls. Worth it for: high-stakes decisions, council votes, public-facing output. Skip for: routine execution, log noise.


## Round 5 — Chairman of the council ✅
- **Council verdict (codex):** **Chairman = role, not model** (best default). Any capable model plays the role; prompt rules define behavior. User pick is optional override.
- **Why not "strongest model":** creates a permanent favorite, no rotation, no audit of why
- **Why not "rotated per topic":** inconsistent output style and authority
- **Implementation in War Room:** `council_chamber` panel gets a `chairman_role` config; chairman prompt is a stable template (synthesize, call out disagreements, preserve minority warnings, recommend action with confidence level)


## Round 6 — Adversarial review (red-team / blue-team) ✅
- **Council verdict (codex):** **Yes, dedicated red-team role.** Prevents groupthink, catches weak assumptions, stress-tests hallucinations.
- **Use red-team for:** strategy, security, public-facing output, architecture decisions, code that touches money/data/PII
- **Skip red-team for:** low-risk drafts, routine summaries, brainstorming, internal notes — use lightweight self-checks there
- **Maps to War Room:** could be a 4th voice in the council (boss/manager/council/red-team), OR a `qa-lead` / `security-lead` role played adversarially in the right contexts. Per CLAUDE.md, this is a **Taste** decision (not Mechanical, not User Challenge) — Boss can recommend, Saiyudh decides.


## Round 7 — Cost-aware routing ✅
- **Council verdict (codex):** **Task-routing classifier** is best default. Cheap model first, escalate on failure OR when risk/complexity/reversibility exceed threshold.
- **Pattern hierarchy for War Room:**
  1. **Classifier/router** (cheap) — decides which model to use based on risk + complexity + reversibility
  2. **Cheap-first** — default for routine tasks (qwen2.5:3b, mini models)
  3. **Escalation** — if cheap fails or low confidence, escalate to medium
  4. **Strong-first** — only for high-risk planning, incident diagnosis, security-sensitive bash, architecture
  5. **Parallel** — only for high-blast-radius final decisions (destructive commands, conflicting evidence, public output)
- **Maps to War Room:** `army.py` already has `worker` selection. Add a `risk_classifier()` step before worker selection.


## Round 8 — Failure modes of multi-LLM councils ✅
- **Council verdict (codex):** 4 named failure modes with 1-line mitigations:
  1. **Groupthink convergence** → force independent first-pass answers before discussion
  2. **Authority bias** → blind model identities, weight evidence over confidence
  3. **Error amplification** → require source checks or tool verification for factual claims
  4. **Cost/latency blowup** → cap rounds, use early stopping, escalate only hard cases
- **War Room implication:** every council_chamber run should log (a) the 4 mitigations it applied, (b) any that failed, so we can audit groupthink over time


## Round 9 — Right mix for War Room's council ✅
- **Council verdict (codex):** **qwen2.5:3b is too weak to be a real second opinion.** Pull a 7B model. Prefer Nemotron if performance is acceptable.
- **Recommended council voices:**
  1. **Codex (gpt-5.5)** — strong, default chairman candidate
  2. **Ollama Nemotron (or qwen2.5:7b)** — local second opinion, reasoning/critique-oriented
  3. (Future) **Codex mini or o3-mini** — third voice for ties
- **Action item:** pull `nemotron` (~7B) and re-test the council for Round 1 of Loop 2 — currently only qwen2.5:3b is pulled, which is too weak to catch codex's blind spots
- **Cost:** 4-8 GB disk per model. The War Room host has plenty of headroom.


## Round 10 — Council operational checklist ✅
- **Council verdict (codex, synthesized from R8 mitigations + R9 upgrade + general practice):**
  1. **Version + freeze** every council prompt, rubric, model config, routing rule — every decision must be reproducible
  2. **Disagreement handling** — require explicit escalation/human-review/fallback when votes are split, low-confidence, or contradict safety/business rules
  3. **Monitor per-model + per-role metrics** — accuracy, override rate, drift, latency, cost, refusal rate, incident-linked decisions
  4. **Full audit trail** from final action back through all council inputs, votes, overrides — with retention, access controls, redaction
  5. **Periodic council eval** — replay past decisions against current council config, measure drift, trigger prompt-review cycle (ties back to Loop 2 R9 "weekly prompt review with eval gate")
- **War Room implementation:** add a `council_audit_log` table (per-agent, per-run, per-vote) + a weekly `council_eval.py` job


---

# LOOP 4 — Specialized Segmented Agents / Departments

## Round 1 — crewAI / MetaGPT / ChatDev / AutoGen role libraries ✅
- **Council verdict (codex, abridged):**
- **Software engineering team:** CrewAI `Senior Engineer/Code Reviewer/Tester`; MetaGPT `Architect/Engineer/QA`; ChatDev `CEO/CTO/Programmer/Reviewer`; AutoGen `group chat` for debate/escalation
- **Research team:** CrewAI `Research Specialist/Writer/Editor`; MetaGPT `PM/Architect` (for "requirements researcher + synthesis architect"); ChatDev `CEO/CTO discussion phase`; AutoGen deep-research packs
- **Marketing/content team:** CrewAI `B2B Tech Content Strategist/Researcher/Editor`; MetaGPT `PM/Project Manager/QA` → `Campaign Strategist/Editorial PM/Brand QA`; ChatDev `CEO/Reviewer/Tester` → `Positioning Lead/Copy Reviewer/Audience Tester`
- **Finance/ops team:** CrewAI `Financial Analyst/Reporting Analyst/Data Analyst`; MetaGPT PM/Architect/QA → `Ops Planner/Process Architect/Controls QA`; ChatDev `CEO/CTO/Reviewer` → `Ops Lead/Systems Lead/Risk Reviewer`; AutoGen `analyst + tool-enabled executor + reviewer`
- **War Room's existing 13+ agents** are 80% of the engineering team already. Missing: dedicated **researcher + content/marketing + finance/ops** departments.


## Round 2 — alirezarezvani/claude-skills (the deliverable format) ✅
- **Repo:** `alirezarezvani/claude-skills` (cloned). Reference for the *structure* of our `Department Starter Kit` doc.
- **Top-level departments** (30+): `agents/`, `business-growth/`, `business-operations/`, `c-level-advisor/`, `commercial/`, `compliance-os/`, `engineering/`, `engineering-team/`, `finance/`, `marketing/`, `marketing-skill/`, `orchestration/`, `productivity/`, `product-team/`, `project-management/`, `ra-qm-team/`, `research/`, `research-ops/`, `standards/`, `templates/`
- **Agent roles in `agents/`:** business-growth, c-level, engineering, engineering-team, finance, marketing, personas, product, project-management, ra-qm-team
- **Multi-CLI skills:** `.claude/`, `.codex/`, `.gemini/`, `.hermes/`, `.vibe/` (one repo = skills for 5+ AI CLIs)
- **Council verdict (Boss, no codex this round — direct synthesis):** **Adopt this structure for War Room's Department Starter Kit.** Each department folder gets: `SOUL.md` (agent identity), `TOOLS.md` (tools it can use), `AGENTS.md` (other depts it reports to), `SKILLS.md` (reusable skills), `CONVENTIONS.md` (do/don't).
- **Deliverable format target:** one `.md` per department, 200-500 lines, copy-pasteable into `backend/jarvis_company_os/departments/<dept>/`


## Round 3 — Anthropic "Building Effective Agents" (5 patterns) ✅
- **Council verdict (codex), mapped to War Room departments:**
  - **Prompt chaining** → **Strategy Desk** (mission broken into ordered handoffs, one artifact at a time)
  - **Routing** → **Triage Desk** (classifies issues, sends to specialist path)
  - **Parallelization** → **Intelligence Cell** (multiple analysts in parallel, then consolidate)
  - **Orchestrator-workers** → **Command Center** (one lead decomposes mission, coordinates specialists)
  - **Evaluator-optimizer** → **Red Team / QA Desk** (critiques outputs, loops revisions until good enough)
- **Critical rule from Anthropic:** **For simple tasks, don't use agents — use a single LLM call.** War Room should always check: "could this be a single chat message?" before spinning up a department.


## Round 4 — Boss/Manager/Worker pattern (org chart vs management protocol) ✅
- **Council verdict (codex):** **War Room has the org chart, but NOT the full management protocol.**
- **Manager tier references:** Chief of Staff model, Scrum Master/Program Manager coordination, Kanban flow control
- **Worker tier references:** Tiger Team execution model, Scout/recon patterns (security/military), MapReduce/fan-out-fan-in
- **Boss tier references:** CEO/CFO/COO operating models, OKR-driven prioritization, board-approval gates
- **What War Room is missing:**
  - Explicit **decision rights per tier** (who can approve what, up to what budget)
  - **Handoff schemas** (what format Manager→Worker, Worker→Manager, Manager→Boss)
  - **Escalation rules** (when to escalate, to whom, with what evidence)
  - **Task lifecycle states** (draft → ready → in_progress → blocked → review → done → archived)
  - **Success criteria per task type** (what "good" looks like)
  - **After-action learning loop** (postmortem after every completed mission, log to memory bank)


## Round 5 — Domain-specific department starter packs ✅
- **Council verdict (codex) — concrete picks per domain:**
  - **Engineering team:** **Phalanx** (planner/builder/reviewer workflows, failing-CI diagnosis, PR creation). Best for War Room's existing `eng-lead + qa-lead + security-lead` trio.
  - **Research team:** **ResearchPilot** (literature review, related-work synthesis). Pair with a lightweight "experiment designer" agent for hypothesis/test-plan output. Maps to our `scout` + `researcher` agents.
  - **Ops team:** **Aurora** (SRE incident response, cloud/K8s investigation) OR **OpenClaw Incident Response** (simpler template/config to start). Maps to a new `ops-lead` agent (currently missing from our 13+).
- **Gap identified:** War Room has no **ops-lead** role. Recommend adding one for incidents, deployments, monitoring.


## Round 6 — Skill marketplace pattern ✅
- **Council verdict (codex):**
  - **Don't inline skills into SOUL.md** — becomes hard to review, version, test, selectively load. Inline only tiny routing stubs like "load `skills/research.md` for X."
  - **Use separate `skills/*.md` files** per skill (frontmatter: name, purpose, triggers, required tools, maturity)
  - **Add a lightweight registry** — `skills/registry.json` or `skills/README.md` with name, purpose, triggers, required tools, maturity. Gives marketplace behavior without platform lock-in.
  - **Stay compatible with Anthropic-style skills** — structure War Room skills so they can later export/import via `npx skills add <repo>`, but keep local registry as source of truth.


## Round 7 — Anthropic "When to use agents" ✅
- **Council verdict (codex), key rules:**
  - **Use agents when:** multi-step, decision-heavy, tool-using, long horizon, or needs context/memory across calls
  - **Don't use agents when:** a single LLM call works, or the steps are deterministic (just code)
  - **Right ceiling:** if you can express the task in <10 lines of imperative Python, you don't need an agent
- **War Room implication:** every CouncilChamber invocation should be tagged with `task_complexity` (low/med/high). Low → single LLM call. Med → 1-2 agents. High → 3+ agents + human-in-the-loop.


## Round 8 — Boss-Manager-Worker escalation rule ✅
- **Council verdict (codex):** **Escalate on blocker or threshold breach, not by default.**
- **The rule:**
  - **Worker → Lead:** when blocked, OR exceeded budget/time/risk/stake limit, OR affects another tier's mandate
  - **Lead → Manager:** for cross-lead coordination, budget, or deadline risk
  - **Manager → Boss:** only for strategic tradeoffs, major stake exposure, or authority the Manager cannot exercise
- **Confidence is advisory:** `confidence < X` triggers review/second-opinion/scout-council, **not** automatic Boss escalation unless paired with high stakes or irreversible impact
- **War Room fit:** codify this as the `escalation_policy.md` referenced by every agent's SOUL.md


## Round 9 — Department Starter Kit skeleton ✅
- **Council verdict (codex), per-department file list:**
  - **Engineering:** `SOUL.md`, `TOOLS.md`, `AGENTS.md`, `CONVENTIONS.md`, `POSTMORTEMS.md`
  - **Research:** `SOUL.md`, `METHODS.md`, `SOURCES.md`, `SYNTHESES.md`, `AGENTS.md`
  - **Marketing:** `SOUL.md`, `BRAND.md`, `CAMPAIGNS.md`, `ASSETS.md`, `METRICS.md`
  - **Finance/Ops:** `SOUL.md`, `BUDGETS.md`, `RUNBOOKS.md`, `INCIDENTS.md`, `AGENTS.md`
  - **Product:** `SOUL.md`, `ROADMAP.md`, `REQUIREMENTS.md`, `AGENTS.md`, `DECISIONS.md`
  - **Security:** `SOUL.md`, `THREAT_MODEL.md`, `CONTROLS.md`, `INCIDENTS.md`, `AGENTS.md`
- **Common files in every dept:** `SOUL.md` (identity), `AGENTS.md` (peers/reports), one or more department-specific operating docs
- **Folder target:** `backend/jarvis_company_os/departments/<dept>/` with `skills/registry.json` at the top
- **This is the doc the user asked for as the "Department Starter Kit" deliverable** — to be expanded in `docs/RESEARCH_FINDINGS.md`


## Round 10 — Skill composition patterns ✅
- **Council verdict (codex):** **Pre-flight selection (router picks 2-3) + lazy activation as fallback.**
- **Patterns ranked for War Room:**
  1. **Pre-flight selection** — router classifies task, loads top 2-3 likely skills before agent starts. Best default: good coverage, bounded context cost, no mid-task stalls.
  2. **Lazy activation** — skills expose compact trigger metadata; agent activates additional skill only when evidence crosses a trigger. Handles surprises without first-turn heaviness.
  3. **On-demand (skip)** — cheaper in theory, but adds latency during incident/debug loops where War Room needs fast turns.
  4. **All-loaded (skip)** — context blowup, slow, expensive.
- **Maps to War Room:** every agent's SOUL.md gets a `skill_router.md` block (2-3 default skills) + a `lazy_triggers.md` block (skills to activate on signal).


---

# LOOP 5 — Dashboard Best Practices

## Round 1 — Langfuse ✅
- **Repo:** `langfuse/langfuse` (28.7k⭐, MIT + commercial). Self-hostable.
- **What:** LLM observability — traces, evals, prompt management, datasets.
- **Council verdict (codex):** **Adopt as the default observability layer** for War Room. Drop-in for any LLM call. Maps to our `AuditStrip` panel + adds eval + datasets.
- **Why:** trace every LLM call (who, what model, what prompt, what response, latency, cost, feedback). Lets us debug and improve.


## Round 2 — Langfuse vs LangSmith vs Helicone vs OpenLLMetry ✅
- **Council verdict (codex):** **Langfuse + OpenLLMetry/OTel.** Use Langfuse now; keep OTel standard underneath so we can swap backends later.
- **Why not LangSmith:** excellent but commercial/hosted-product, weaker for "OSS first / self-host / free"
- **Why not Helicone as core:** too narrow — just API-call logging proxy, misses local model traces, agent spans, tool calls, evals
- **Why OpenLLMetry:** it's the OpenTelemetry standard for LLM traces — gives portability. Wrap it in Langfuse UI for human use.


## Round 3 — Arize Phoenix vs Langfuse ✅
- **Council verdict (codex):** **Langfuse as default operational ledger; Phoenix as evaluation/diagnostics bench.**
- **Langfuse = day-to-day ops** (traces, sessions, datasets, scores, annotations, release comparison)
- **Phoenix = when quality drifts** (LIME/SHAP, RAG analysis, clustering, deeper quality diagnosis)
- **Pragmatic split for War Room:** Langfuse on the hot path (every LLM call), Phoenix on-demand (drill in when "why is this model changing?")


## Round 4 — LangFlow vs Flowise ✅
- **Council verdict (codex):** **Do not adopt either as War Room's core.** Both are visual/low-code; War Room is already code-first with 19 React panels. Adding either would create a second runtime/control plane.
- **Security flag (critical):** both projects have had serious RCE-class issues around executable workflow components. Don't expose them in a high-value ops UI.
- **Use as sandbox only:** LangFlow as a prototyping sidecar (Python, MCP export, observability hooks). Port useful flows into War Room's typed services.
- **Conclusion:** keep building War Room workflows in code.


## Round 5 — n8n integration (already running in user's Docker) ✅
- **Council verdict (codex):** **n8n = automation/action layer around War Room; War Room = reasoning/org control.** Don't let n8n orchestrate the 13+ agent org.
- **Use n8n for:**
  - **External trigger source** (webhooks in, cron, email watchers feeding events)
  - **Post-action executor** (agents call n8n workflows for repeatable side effects: post to Discord, update Notion, log to Sheets, fire webhooks)
- **Don't use n8n for:** full integration (orchestrating agents — too brittle for state, branching, retries, budgets, cross-agent context)
- **War Room boundary:** routing + agent assignment happens INSIDE War Room; n8n is the "hands" not the "brain"


## Round 6 — VectorShift / Vellum ✅
- **Council verdict (codex):** **Skip for core dashboard. Defer integration.**
- **Why skip:** no-code builders add vendor coupling + runtime opacity; War Room needs native code for dashboards, permissions, data freshness, audit logs, reliability
- **Optional pilot:** Vellum/VectorShift behind ONE non-critical feature (e.g. "summarize this incident" or "generate investigation checklist")
- **Recommendation:** build War Room dashboard as first-party


## Round 7 — Real-time WebSocket patterns ✅
- **Council verdict (codex):** **Snapshot + delta with topic subscriptions.** Keep full event stream only as admin/debug mode with rate limits.
- **Pattern hierarchy:**
  1. **Snapshot + delta** (best UX, best recovery after reconnect) — initial state, then ordered deltas
  2. **Subscription-based** (clients subscribe to agent IDs, rooms, runs, alerts, log levels) — operators watch subset
  3. **Full event stream** (admin/debug only) — too expensive for normal clients
- **War Room implementation:** extend `backend/core/websocket.py` to support topic subscriptions + snapshot+delta protocol
- **Why this matters:** the current 19 panels (AgentConstellation, MemoryNexus, MissionControlOverview, CouncilChamber) all need real-time updates without flooding the client


## Round 8 — Command deck pattern (theatrical control room) ✅
- **Council verdict (codex):** **Star/warp shell + tactical density inside.**
- **Why each style:**
  - **Star/warp-style** (center hub + orbiting panels) — **War Room's identity** per spec ("living bridge, not a board"). Use as the main command deck
  - **War-room table** (tactical flat, dense) — good for drill-down mode, weaker as primary identity
  - **Ops console** (sidebar + main + log) — practical but too conventional, feels like an admin tool
- **Implementation:** **AgentConstellation** is the existing star-style centerpiece (3D read-only). Surround it with **table-like dense panels** (KanbanFleet, ArmyOperations) and **console logs** (AuditStrip, SessionDrawer) as secondary surfaces. The MissionControlOverview is the flat radar — keep it as a "tactical flat" mode.
- **Principle:** spectacle at the center, density at the edges, logs in the gutter.


## Round 9 — 3D vs 2D visualization ✅
- **Council verdict (codex):** **Split them. 3D for visualization/status. 2D xyflow for authoring topology.** Sync the same graph model.
- **Why split:**
  - **3D (AgentConstellation)** — presence, depth, motion, spatial clustering. Keep as the "live situational view" centerpiece.
  - **2D (xyflow)** — precision, hit testing, drag, connect, label, inspect, undo, diff, keyboard. Editing work needs accuracy.
- **3D editor risk:** hit testing, occlusion, camera control, edge routing, dense labels, accessibility — all consume time without improving core editing
- **Sync model:** same graph data (from `/companies/{id}/topology`) feeds both views. Edits in 2D update 3D in real-time.
- **This validates the D-2026-06-08-topology-editor brief** — 2D xyflow editor + 3D read-only constellation, sharing one data source


## Round 10 — Dashboard Pattern Library ✅
- **Council verdict (codex), 5 patterns for the War Room dashboard:**
  1. **Real-time** — every critical state change appears instantly, with clear freshness and sync status
  2. **Observability** — surface health, latency, errors, confidence directly in the workflow
  3. **Command-deck** — primary decisions, actions, and exceptions in one dense operational surface
  4. **Command center UX** — prioritize scanning, triage, comparison, repeated action over presentation
  5. **Default editor mode** — open in the safest high-control editing state, with preview/review one click away
- **Maps to War Room panels:**
  - Real-time → WebSocket snapshot+delta (R7)
  - Observability → Langfuse + AuditStrip (R1)
  - Command-deck → AgentConstellation (3D centerpiece, R8/R9)
  - Command center UX → KanbanFleet, ArmyOperations, MissionControlOverview (tactical surfaces, R8)
  - Default editor mode → 2D xyflow topology editor (R9), with dagre auto-layout, "preview" toggle before save


---

# 🎯 ALL 5 LOOPS COMPLETE — 50/50 council consultations

See **`docs/RESEARCH_FINDINGS.md`** for the master synthesis tying all 50 rounds together.
