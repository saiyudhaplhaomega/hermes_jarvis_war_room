# Jarvis War Room Dashboard - Phase 2 Specification
```yaml
name: jarvis-dashboard-phase2
version: 1.1.0
stakeholders: [Boss (Claude), Manager (Codex), Challenger (DeepSeek/GLM), Secretary (Qwen), Worker (MiniMax)]
date: 2026-05-29
status: APPROVED BY COUNCIL
```

---

## 1. Vision Statement

Transform the Phase 1 static HTML dashboard into a fully animated, real-time, dramatic theatrical command deck. Every panel must feel alive. Constellations orbit in 3D with depth. Achievements unlock with particle effects. Conversations scroll like a cinematic log. Discord threads appear in real-time. Agents pulse with heartbeat. The dashboard is not a board — it is a living bridge.

Core philosophy: "More than a kanban. A bridge between worlds."

## 2. Key Features (The Twelve Elevations)

| # | Feature | Phase 1 State | Phase 2 Target | Section |
|---|---------|---------------|----------------|---------|
| 1 | Agent Constellation | Flat CSS stars | **Three.js 3D orbit map** | 3.1 |
| 2 | Conversation Log | ABSENT | **Transcript viewer with session search** | 3.2 |
| 3 | Discord Thread Map | ABSENT | **Real-time thread feed + webhooks** | 3.3 |
| 4 | Achievement Theater | ABSENT | **XP, badges, unlocks, confetti** | 3.4 |
| 5 | WebSocket Push | 5s polling | **WebSocket/SSE live push** | 3.5 |
| 6 | Audit Log Panel | Logged to disk | **Rendered in UI with filtering** | 3.6 |
| 7 | Agent Heartbeat | Static orbs | **Live status + task progress** | 3.7 |
| 8 | Cost EKG Ribbon | CSS animation | **Real data-driven SVG wave** | 3.8 |
| 9 | systemd Service | Manual start | **Auto-start on boot** | 3.9 |
| 10 | Headscale VPN | BROKEN | **Working config + remote access** | 3.10 |
| 11 | Memory DNA Helix | SVG sine waves | **3D rotating double strand** | 3.11 |
| 12 | Decision Council Chamber | Tier badges | **3D chamber view with voting record** | 3.12 |

## 3. Feature Specifications

### 3.1 Three.js Agent Constellation Map
Replace the 2D CSS div constellation with a Three.js canvas element.
- Agents rendered as 3D spheres (not flat divs) with bloom/glow.
- Connections as dashed 3D lines, animated with a moving texture (data flow).
- Camera: auto-orbits slowly. User can drag to rotate, scroll to zoom.
- On hover: agent name tooltip + status summary.
- Agents pulse in 3D space with individual animation offsets.
- Background: starfield shader, not radial CSS gradient.
- Performance: <30 draw calls, 60fps on integrated graphics.

### 3.2 Conversation Transcript Viewer
**New panel:** Full-width bottom drawer (toggle-able) that streams session logs.
- Pulls from Hermes SQLite session DB via new API endpoint.
- Live search bar: FTS over all session content.
- Playback mode: "Replay" a session step by step.
- Per-message attribution: which model, which agent profile.
- Color-coded by agent role (Boss=red, Manager=blue, Worker=green, etc.).
- Collapsible thread view for multi-message exchanges.
- Export to JSON/Markdown buttons.

### 3.3 Discord Thread Integration
**New panel:** Real-time Discord thread list from connected bots.
- Uses Discord Bot Gateway WebSocket (or webhooks if gateway unavailable).
- Thread cards show: channel name, thread title, participant bots, last message.
- Click thread opens a mini-message panel.
- Visualization: threads rendered as nodes orbiting a Discord planet.
- Auto-join indicator: which bots are "present" in which threads.

### 3.4 Achievement Theater
**Overlay system:** Non-blocking achievement announcements.
- Badge system with SVG icons, unlock animations.
- Categories: Builder (deploys, commits), Scholar (docs written), Commander (dispatches), Pioneer (firsts).
- XP bar with level progression.
- Unlock triggers detected by backend (e.g., first deployment, 100th commit, etc.).
- Confetti canvas overlay on unlock.
- Achievements persisted in `~/.hermes/state/achievements.json`.
- Frontend: pop-up toast with animation, stores all earned in sidebar.

### 3.5 WebSocket Live Push
Replace all 5-second polling with WebSocket push where applicable.
- Backend: add `/ws` endpoint using FastAPI websockets.
- On aggregator refresh, broadcast updated JSON to all connected clients.
- Frontend: multiplexed subscriptions per panel type.
- Fallback: if WebSocket fails, degrade to SSE, then back to polling.
- WebSocket message schema typed via Pydantic models.

### 3.6 Audit Log Viewer
**New panel in footer bar:** System events with filtering.
- Reads `~/.hermes/state/audit/audit.jsonl` via backend.
- Filter by: severity (info/warn/error), category (auth, dispatch, data), time range.
- Color-coded rows with expand-on-click for full details.
- Live stream mode: append new log lines as they are written.

### 3.7 Agent Heartbeat + Live Task Progress
Enhance existing agent constellation with live state information.
- Heartbeat: API pings every agent's Hermes profile health endpoint.
- If dead >5min: orb turns gray, connection dim, tooltip shows "Last seen at 07:14".
- Current task: agents show a label "Working on: [task name]" above their orb.
- Progress ring: circular SVG path around the orb showing task completion %.
- Model in use: subtle secondary label below orb name.
- CPU/memory of host machine (optional future).

### 3.8 Cost EKG Ribbon
Enhance existing SVG cost animation to use actual(real) cost data.
- Every API call logged by the aggregator is added to a shared cost vector.
- Vector flushed to the EKG display every 100ms.
- Color: baseline green. Spike on high cost turns yellow, budget danger = red flash.
- Historical: ability to scroll back 24h via a scrubber beneath the ribbon.
- Baseline horizontal line showing $0.00, labeled Y-axis with $scale.

### 3.9 Systemd Auto-Start
Register jarvis-dashboard backend as a systemd service.
- Unit file: `jarvis-dashboard.service` targeting port 8502.
- Depends on: network-online.target.
- Restart always, restart delay 10s.
- Log to journal with structured JSON.
- Frontend static server also registered (port 8503) or unified nginx proxy.
- Daily restart at 04:00 via systemd timer.

### 3.10 Headscale VPN Fix
Resolve the DNS prefix configuration error in Headscale v0.28.0.
- Root cause: `ip_prefixes` top-level key is not recognized by this version.
- Fix: determine the correct key (likely nested under `prefixes:` with `ipv4:` subkey, or under the `derp:` block).
- Verify by starting headscale and registering a node.
- VPN encapsulation: dashboard becomes accessible over 100.64.x.x without exposing port 8502 to the public internet.

### 3.11 3D Memory DNA Helix
Replace 2D sine wave helix with a 3D CSS or Three.js double helix.
- Rotating double strand with base-pair connections.
- Interactivity: hover over a "rung" shows the memory fact it represents.
- Click to zoom into that memory node.
- Color: approved facts = blue strand, pending = purple, contradictions = red.

### 3.12 Decision Council Chamber
**New fullscreen or expanded panel:** Visual representation of the council.
- 3D or 2.5D room with seats for each council member.
- Seating determined by role (Boss = raised throne, Manager = podium, Secretary = desk, Workers = stands).
- Each decision displayed as a scroll above the chamber.
- Voting records: who proposed, who challenged, who approved.
- History: scroll back through past council sessions.
- Achievement: "Honorary Chamber Member" for reaching N decisions.

## 4. Non-Goals
- NOT replacing Hermes CLI/TUI. The dashboard is supplementary.
- NOT a chat replacement for Discord. Threads are displayed in-view only.
- NOT public hosting. Must remain localhost-only or VPN-only.
- NOT replacing the existing Kanban UI — it is already usable.

## 5. Technical Decisions Summary
- Three.js v0.160 via CDN (no bundler to keep deployment simple).
- WebSocket over Socket.IO? No — native WebSocket to keep backend simple.
- Database for achievements: flat JSON file (not SQL). Low transaction load.
- Discord integration: use existing webhook subscription skill first, gateway as future.

---

## 6. Premium Mission Control + Dynamic Role Matrix Addendum

Date: 2026-06-01T09:17:30Z
Status: IMPLEMENTED AS DASHBOARD-LOCAL OVERLAY

### 6.1 Scope
Upgrade the existing React War Room rather than replacing it with the tutorial's one-file dashboard. The pasted tutorial is treated as inspiration for visual language, live operations presentation, version visibility, and operator role management.

### 6.2 Non-Negotiable Constraint
The dashboard must not create, delete, or modify Jarvis profiles or agents. Role/model selection is a dashboard-local overlay only. Profile configs, prompts, Discord bindings, `.env` files, and memory remain untouched.

### 6.3 New Capability
Add a Role Matrix / Model Router panel where Saiyudh can map operational roles to existing Jarvis agents and preferred provider/model pairs. This enables dynamic role assignment without mutating the Company OS topology.

### 6.4 Data Contract
Role mappings are stored in dashboard-local JSON under the dashboard state directory. API responses must explicitly include `writes_profile_configs: false` so the UI and smoke tests can verify the safety contract.

### 6.5 UX Requirements
- Premium dark glassmorphism Mission Control shell.
- Header version badge and live 24-hour clock.
- Overview/Command Deck with agent radar, project scope, cards, decisions, memory, and health signals.
- Role Matrix with editable role, agent, provider, model, status, and notes fields.
- Existing panels must remain present: Agent Constellation, Memory Nexus, Decision Log, Kanban Fleet, Dispatch Terminal, Discord Nexus, Council Chamber, GitHub Workspace.

### 6.6 Security Requirements
- All role endpoints require existing dashboard auth.
- Role writes must be atomic.
- User-controlled identifiers must reject path-like strings.
- No profile config writes are allowed.
- No secrets are logged or embedded in committed frontend code.

APPROVED BY: Saiyudh green signal, implemented by Jarvis Manager (Codex GPT-5.5)

---

## 7. Army Operations / CLI Worker Orchestrator Addendum

Date: 2026-06-03T07:11:34+08:00
Status: APPROVED FOR IMPLEMENTATION BY SAIYUDH; COUNCIL-FIRST REVIEW COMPLETED

### 7.1 Goal

Add a Conductor-style Army Operations module to the existing War Room Dashboard. Hermes remains the control plane. The dashboard becomes the operator view for durable CLI-worker runs: create, observe, inspect logs, review diffs, approve/reject, rerun, and learn from feedback.

### 7.2 Non-Negotiable Constraints

- Do not replace the existing War Room dashboard or remove any current panels.
- Do not migrate to Next.js for this phase; keep the current React/Vite SPA.
- Do not mutate Hermes profiles, prompts, `.env` files, Discord bindings, or global skills from dashboard actions.
- Do not push to main or merge automatically.
- Do not run worker commands through `shell=True`.
- Do not expose worker shells publicly.
- Do not log secrets, dashboard auth tokens, or provider keys.
- Approval is a gate, not a blind merge: smoke/security/tutorial/memory requirements must be visible before release.

### 7.3 Capability Scope

The new module adds:

- Worker capability discovery: Claude Code available, Codex unavailable until installed, MiniMax planned.
- Run registry: dashboard-local SQLite/JSON state under dashboard-owned state paths.
- Run lifecycle: queued, running, completed, failed, needs_review, approved, rejected.
- Safe spawn endpoint for a controlled worker task.
- Log capture and log viewing.
- Diff endpoint for run workspace changes.
- Reject reason capture and rerun prompt construction.
- Dashboard UI: Army Operations panel with worker roster, run board, run detail, logs, diff, and controls.

### 7.4 Worker Roster v1

- Claude Code: enabled if `claude` binary exists. Primary v1 worker on this host.
- Codex: shown as unavailable because `codex` binary is not currently installed.
- MiniMax: planned adapter only; no execution path until endpoint/auth is explicitly verified.

### 7.5 Safety Contract

All Army Operations API responses that expose mutating actions must include `writes_profile_configs: false`. Dashboard actions write only dashboard-owned run state and run workspaces unless a later human-gated provisioning step explicitly approves broader access.

### 7.6 Release Gate

This feature is not releasable until:

- backend tests pass,
- frontend build passes,
- runtime smoke validates health, workers, run creation, and UI render,
- security review checks path traversal, shell injection, token leakage, and profile mutation risk,
- tutorial/docs explain every new backend file, frontend component, endpoint, and test,
- decisions are logged here and mirrored to Obsidian.
