# Decision — Project Topology Editor v2 (incorporates 8+ rounds of research)

Date: 2026-06-08
D-ID: D-2026-06-08-topology-editor
Version: v2 (supersedes v1 draft of 2026-06-08)
Status: DRAFT — pending Saiyudh approval
Project: Jarvis War Room Dashboard
Owner: Boss
Predecessor: `decisions/D-2026-06-08-topology-editor.md` (v1, replaced by this)

## What changed since v1

After 8+ rounds of research (see `docs/RESEARCH_LEDGER.md` for the
full log), v1 was too narrow. v2 incorporates the new findings:

- **v1 picked React Flow.** v2 keeps that pick but now **also** plans
  for the 3D companion (R3F force-graph) and the **animation layer**
  (Framer Motion + the `Animate-ReactFlow-Nodes` pattern).
- **v1 only edited topology.** v2 frames the topology editor as the
  **first panel in a larger Command Deck arc** (see Horizon 1
  expansion below).
- **v1 assumed separate War Room projects.** v2 now references
  the proven architectures of `humanlayer/humanlayer` (hld/hlyr/wui),
  `proinsight-io/crewmeld` (monorepo + framing), and
  `xvirobotics/metabot` (supervisor over self-improving org).

## Context

`docs/FEATURE_INVENTORY.md` line 39 lists "True topology canvas with
companies/teams/agents/edges editing" under **Pending / must not be
faked**. The `jarvis_company_os` backend already exposes
`GET /api/plugins/jarvis-dashboard/v1/companies/{id}/topology`
returning the `{nodes, agents, edges}` shape, and `POST /edges` for
adding edges (`backend/jarvis_company_os/router.py:29-110`).

What's missing is the **editable frontend surface** that lets Saiyudh
drag agents, add/remove `reports_to` and `collaborates_with` edges,
and persist changes — without mutating Hermes profile configs (per
invariant §3.5 "Role Matrix must not mutate Hermes profile configs").
The current `AgentConstellation.tsx` is read-only Three.js
visualization, not a topology editor.

This is Horizon 1, item 1 of the 2026-06-08 roadmap (see
`docs/ROADMAP.md` when written).

## ELI10

The War Room shows your AI company as a 3D constellation of orbs
(agents) and lines (who reports to whom). Right now you can look at it
but you can't change it. We want a 2D canvas where you can drag the
agents around, draw new "reports to" / "collaborates with" lines
between them, and save it back to the company. The 3D constellation
keeps working as a read-only view of the same data. And — here's the
new bit — every time an agent moves or a handoff happens, the
animation should *feel* like a real org: a hand-off animation
between the CTO and Eng-Lead when a task routes.

## Stakes

- **If we pick wrong:** the War Room gains a half-baked visual editor
  that either (a) duplicates state and drifts from the company OS
  source of truth, or (b) accidentally mutates Hermes profile
  configs, violating the strongest existing invariant. The 3D
  constellation must keep working unchanged.
- **Blast radius:** Project-scoped (per `CLAUDE.md` §"Project scope").
  No global mutation, no profile writes, no SOUL.md writes.
- **Reversibility:** All changes additive. New panel, new
  `frontend-react/src/components/ProjectTopologyEditor.tsx`, optional
  two new backend endpoints. Easy revert via `git revert`.

## What the research told us

Full log: `docs/RESEARCH_LEDGER.md` (8 rounds, ~50 repos surveyed).
The top 10 Tier-A references for this decision are:

| Repo | ⭐ | Why it matters here |
|---|---|---|
| xyflow/xyflow | 37k | The 2D editor. Was `reactflow`, now `@xyflow/react` (v12) |
| dagrejs/dagre | 5.7k | Auto-layout. MIT. Now in TypeScript |
| vasturiano/react-force-graph | 3.2k | 3D companion (R3F variant at `r3f-forcegraph`) |
| framer/motion | n/a | `layoutId` for handoff animations |
| CubeStar1/dsa-visualizer | 26 | React Flow + Framer Motion example |
| cx-shay-shimonov/Animate-ReactFlow-Nodes | 0 | Exact technique for animating node positions |
| halmadany/org-visualizer | 0 | Zustand store pattern for editor state |
| randomdrake/react-flow-org-chart | 6 | Starting template |
| langflow-ai/langflow | 149k | Drag-drop UX reference (149k stars is the gold standard) |
| humanlayer/humanlayer | 11k | `hld` + `hlyr` + `wui` 3-tier split — our roadmap blueprint |

**Key research insight #1:** Every successful agent dashboard in 2025
splits into 3 layers:
- `hld`-style daemon/state (we have this: `jarvis_company_os` + `army.py`)
- `hlyr`-style CLI/automation (we have this: `army.py` workers)
- `wui`-style web UI (we have this: `frontend-react/`)

We are not behind the curve; we are following the proven pattern.

**Key research insight #2:** Nobody combines:
- editable 2D org chart (React Flow)
- read-only 3D constellation (Three.js or R3F force-graph)
- HITL approval inbox (humanlayer-style)
- Issues-as-coordination-primitive (crewAI-style)
- Cost-as-P&L-per-agent (nobody does this!)

The War Room can have all five. **The differentiation is the P&L
view** — turning the company into a real economic actor.

## Recommendation (v2)

Build a 3-layer **Command Deck** that starts with the topology editor
but is architected to absorb all the other Horizon 1 features
without re-architecting:

### Layer 1 — Topology Editor (this brief)
- Library: **React Flow** (now `@xyflow/react`, MIT, 37k stars)
- Layout: **dagre** for initial positions, user override thereafter
- State: **Zustand** (per `halmadany/org-visualizer`)
- Animation: **Framer Motion** + the `Animate-ReactFlow-Nodes`
  technique (per `cx-shay-shimonov/Animate-ReactFlow-Nodes`)
- New file: `frontend-react/src/components/ProjectTopologyEditor.tsx`
- New endpoints (additive): `DELETE .../edges/{id}`,
  `PATCH .../agents/{id}` (whitelisted fields only)

### Layer 2 — 3D Constellation (read-only companion)
- Library: **`vasturiano/r3f-forcegraph`** (MIT) wrapped in our
  existing `AgentConstellation.tsx` Three.js scene
- Shows the same topology, with `framer-motion`-driven
  camera-flythrough when a node is selected in the editor
- Existing 3D panel stays [PROTECTED]; the new code reads from the
  same `/topology` endpoint, so no schema changes

### Layer 3 — Bridge to Horizon 1 items 2-4
The topology editor becomes the **landing panel** for:
- "Open budget panel for this agent" (Horizon 1 item 2)
- "Open council voting on this edge" (Horizon 1 item 3)
- "View agent card" (Horizon 1 item 4)
This is why we use **Zustand** — it lets all four panels share state
without prop-drilling.

## Options (re-evaluated after research)

| # | Option | Verdict | Why |
|---|---|---|---|
| A | **React Flow + dagre + Framer Motion + Zustand** (recommended) | ✅ | Best-in-class, all MIT, all maintained, all in line with how the top agent dashboards build |
| B | Custom SVG/Canvas | ❌ | Reinvents the wheel. Would burn weeks. No clear upside. |
| C | Reuse Three.js + drag controls in constellation | ❌ | "Editing in 3D is hard" — confirmed by 3+ projects. Conflicts with the [PROTECTED] invariant |
| D | Buy a no-code tool (n8n flow / draw.io embed) | ❌ | Breaks the "single static SPA" deploy model. External dep. |
| E | Use **Langflow's** node editor directly | ❌ | 149k stars but it's a full standalone app, not an embeddable lib. Not appropriate for a "polished War Room" |

A is the clear pick. The combination is "Langflow-grade drag UX,
humanlayer-grade HITL hooks, MIT-everywhere."

## Risks (re-evaluated)

- **Risk A1 (license):** all four libs MIT ✓
- **Risk A2 (bundle):** measure after first build. React Flow is ~50 KB
  gz. Framer Motion is ~30 KB gz. dagre is ~30 KB gz. Total < 120 KB
  added — acceptable. If too large, dynamic `import()` so it only
  loads when the editor panel opens.
- **Risk A3 (state drift between 2D editor and 3D constellation):**
  mitigated — single source of truth = `/topology` endpoint, both
  panels call it, both re-fetch on save.
- **Risk A4 (accidental profile mutation):** mitigated — backend
  endpoint whitelist matches `RoleMatrix` (`label`, `team`, `notes`
  only). Reject any other field with 400. Add a test.
- **Risk A5 (Zustand coupling):** new — by introducing Zustand, we
  add a state lib. Mitigation: the existing React Context stores
  (`DashboardContext`, `ProjectContext`, `KanbanContext`,
  `PanelVisibilityContext`) stay. Zustand is **only** for the
  topology editor's local canvas state. Other panels are unaffected.
- **Risk A6 (over-scope):** v1 was "just the editor." v2 adds the
  3D-bridge + animation layer. Mitigation: deliver in 3 sub-phases
  (see Acceptance), each independently shippable.

## Reversibility

Easy. All additive. No file is renamed. New components, new
endpoints, new dependencies in `package.json`. Single `git revert` of
the merge commit returns to current state.

## Acceptance (revised — 3 sub-phases, each green before next)

A single falsifiable condition per sub-phase. Each sub-phase is
small enough to be a single PR.

### Sub-phase 1 — Static topology view (today's deliverable)
- New `ProjectTopologyEditor.tsx` renders the existing
  `/topology` endpoint using React Flow
- Dagre auto-layout on load
- Read-only — no editing yet
- Click an agent → toast shows agent name + role
- Test: `frontend-react/src/components/ProjectTopologyEditor.test.tsx`
  covers render + click
- Acceptance: visiting the new panel shows the 13+ agents grouped
  by team with edges, identical to the existing backend
- `npm run build` passes
- `scripts/smoke_premium_dashboard.py` updated to also probe
  `/topology` for non-empty response

### Sub-phase 2 — Edit mode (this brief)
- Add `POST/DELETE /edges` and `PATCH /agents` endpoints
  (whitelisted fields only, profile-config mutation rejected)
- `ProjectTopologyEditor.tsx` gains edit mode toggle
- Save button with "unsaved changes" indicator
- Acceptance: drag an agent, add an edge, click Save, refresh —
  state persists
- Tests: `tests/test_topology_editor_api.py` covers
  edge delete, agent patch, profile-mutation rejection
- `docs/FEATURE_INVENTORY.md` line 39 status moved from
  "Pending / must not be faked" to "Implemented (Horizon 1, 2026-06-08)"

### Sub-phase 3 — 3D bridge + animation (this brief)
- New `Topology3DBridge.tsx` using `vasturiano/r3f-forcegraph`
- "View in 3D" deep-link from the editor → 3D camera flythrough
  to the selected agent
- Handoff animation: when a message is sent between agents in the
  WS stream, the edge between them animates (per
  `cx-shay-shimonov/Animate-ReactFlow-Nodes` pattern)
- Acceptance: clicking "View in 3D" opens the 3D scene with the
  selected agent; sending a message in dispatch causes the edge
  to pulse

## Decision class

Mechanical (Taste-light). The 3D constellation is [PROTECTED] per
`FEATURE_INVENTORY.md`. As long as that panel is not modified and no
profile configs are mutated, this is a routine additive feature.

## Files I plan to touch (additive)

### Sub-phase 1
- NEW `frontend-react/src/components/ProjectTopologyEditor.tsx`
- NEW `frontend-react/src/components/ProjectTopologyEditor.test.tsx`
- MODIFY `frontend-react/src/App.tsx` (add new panel)
- MODIFY `frontend-react/src/components/commandMenuLinks.ts`
  (add "Topology Editor" command)
- MODIFY `frontend-react/src/api/client.ts` + `types/dashboard.ts`
  (add typed `topology()` method)
- MODIFY `frontend-react/package.json` (add `@xyflow/react`,
  `dagre`, `dagre-compound`, `framer-motion`, `zustand` deps)
- MODIFY `scripts/smoke_premium_dashboard.py`
- NEW `frontend-react/src/components/ProjectTopologyEditor.css`
  (or inline via Tailwind — match `MissionControlOverview.tsx` style)

### Sub-phase 2
- MODIFY `backend/jarvis_company_os/router.py` (add
  `DELETE /companies/{id}/edges/{edge_id}` and
  `PATCH /companies/{id}/agents/{agent_id}`)
- NEW `tests/test_topology_editor_api.py`
- MODIFY `docs/FEATURE_INVENTORY.md` (move line 39 status)
- MODIFY `docs/TUTORIAL.md` (add 1 paragraph)

### Sub-phase 3
- NEW `frontend-react/src/components/Topology3DBridge.tsx`
- NEW `frontend-react/src/components/Topology3DBridge.test.tsx`
- MODIFY `frontend-react/src/api/client.ts` (add WS subscription
  for `topology_message` events)
- MODIFY `backend/core/websocket.py` (add the event channel)

## Open question for Saiyudh

- Should the editor allow **adding new agents** that don't yet exist
  in any Hermes profile? Or only **editing** existing agents and the
  edges between them? New-agent creation is a heavier flow (SOUL.md,
  HEARTBEAT.md, etc.) that may belong in a separate decision.
  Recommended: editor = edit existing + add/remove edges only. New
  agents go through `RoleMatrix` proposal flow as today.

## Notes for Boss re-review

When Boss's session quota resets, this brief and the implementation
commits (one per sub-phase) are linked so Boss can do a quick pass
against the [PROTECTED] panels list.

## Research provenance

See `docs/RESEARCH_LEDGER.md` for the full log. Every Tier-A reference
in this brief has a row in that file with its URL, star count, and
the round in which it was found.
