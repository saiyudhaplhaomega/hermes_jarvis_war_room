# Decision Log — Phase 2

## Decision 1: Use Three.js CDN, not npm build
**Date:** 2026-05-29
**Context:** Phase 2 spec requires 3D constellation. We could use npm + bundler, but the plugin is a single-file deployable asset.
**Options:**
- A. npm install three + webpack/vite → requires build step, complicates plugin
- B. Three.js CDN + <script src> → no build step, works with existing static server
**Decision:** Option B.
**Rationale:** No build tooling means the plugin remains copy-and-deployable. Three.js r160 CDN is ~600 KB gzipped, acceptable under 5 MB budget. Any performance issues from global scope can be mitigated with `importmap`.
**Council:** Manager proposed, Challenger agreed (bundlers add DX cost for no user benefit), Boss approved (keeping the deploy artifact simple is correct for a plugin).

## Decision 2: Native WebSocket, not Socket.IO
**Date:** 2026-05-29
**Context:** Need live push. Could use Socket.IO for fallback magic, but adds dependency.
**Options:**
- A. socket.io + python-socketio → robust fallback, but heavy dependency
- B. FastAPI native WebSocket + manual fallback logic → zero new deps
**Decision:** Option B.
**Rationale:** FastAPI already has `WebSocket` built-in. Fallback logic (WS → SSE → polling) is ~80 lines of JavaScript we can write ourselves. Socket.IO adds 150 KB client + server complexity for a feature used by 1 admin user.
**Council:** Unanimous.

## Decision 3: Keep frontend as single HTML file, load scripts via <script src>
**Date:** 2026-05-29
**Context:** Spec says "New panels." Could split into React/Next.js or at least separate HTML pages.
**Options:**
- A. Next.js SPA → rich router, but requires build, node, separate port
- B. Enhanced single HTML + modular JS → stays static, loads via CDN
**Decision:** Option B.
**Rationale:** We already have a working static server on :8503. Upgrading it to serve Next.js output means managing another build artifact, `package.json`, `node_modules`. A single HTML file with script tags keeps the deployable footprint tiny.
**Council:** Boss noted we can always revisit Next.js in Phase 3 if the single-file approach becomes unmaintainable.

## Decision 4: Achievement persistence = flat JSON, not SQLite
**Date:** 2026-05-29
**Context:** Need to store unlocked badges, XP.
**Options:**
- A. New SQLite table → consistent with project, but overkill for write-once read-many
- B. `~/.hermes/state/achievements.json` → human-readable, trivial to inspect from CLI
**Decision:** Option B.
**Rationale:** Achievement writes are triggered by human actions (clicks) and aggregator events (background), rate is < 1/min. Flat file is sufficient, debuggable, and survives without schema migrations.

## Decision 5: systemd replaces manual startup, not Docker
**Date:** 2026-05-29
**Context:** Need auto-start on boot. Docker is cleaner isolation, but requires Docker socket + image build.
**Options:**
- A. Docker Compose → cleaner, but adds Docker dependency to a host that may not have it
- B. systemd service units → native to Linux, no extra deps, logs to journalctl
**Decision:** Option B.
**Rationale:** Server already runs Linux with systemd. Using native systemd is more aligned with "self-hosted, native solutions" preference in user profile. Docker would require installing Docker Engine first.

## Decision 6: Headscale config key name unknown, will research before write
**Date:** 2026-05-29
**Context:** Headscale v0.28.0 threw "no IPv4 or IPv6 prefix configured" on `ip_prefixes`.
**Options:**
- A. Guess config keys (prefixes.ipv4, etc) and test iteratively
- B. Research official v0.28.0 schema online before touching config
**Decision:** Option A (fastest path — we are allowed to iterate locally).
**Rationale:** Server is localhost-only, internet is present. Searching 2-3 key names takes less time than reading full schema. We will try `prefixes.v4`, `derp.subnet`, etc, and grep headscale source if needed.
**Risk:** Low. Config file is isolated, previous attempts already known bad.

## Decision 7: Dynamic role/model mapping stays dashboard-local
**Date:** 2026-06-01
**Context:** Saiyudh asked whether role mapping can remain dynamic: select existing agents for roles and select models for roles, without changing Jarvis profiles or agents.
**Options:**
- A. Create or mutate persistent Jarvis profiles/agents for every dashboard role.
- B. Store role/model mappings as a dashboard-local overlay and let the UI use those mappings for display/routing hints only.
**Decision:** Option B.
**Rationale:** The dashboard should be an operator console, not the source of truth for the Company OS topology. Keeping mappings dashboard-local preserves existing Jarvis profiles, Discord bindings, prompts, and agent workspaces while still giving Saiyudh dynamic control over role presentation and preferred model/provider choices.
**Implementation:** `backend/api/roles.py` stores mappings in dashboard-local state, returns `writes_profile_configs: false`, validates safe identifiers, and exposes `/roles`, `/models`, and `/roles/test`. React renders this through `RoleMatrix.tsx`.
**Security Gate:** Auth required, unauthenticated `/roles` returns 401, role API contains no profile config write path, no shell primitives, and no hardcoded dashboard token.

## Decision 8: Army Operations is additive, dashboard-local, and Claude-first until Codex exists
**Date:** 2026-06-03
**Context:** Saiyudh approved integrating the Jarvis CLI Army blueprint into the existing War Room Dashboard and asked Jarvis to use Claude for planning. Discovery found the current dashboard is a Hermes profile plugin with a FastAPI backend and React/Vite SPA, not a git repo. `claude` is installed but `codex` is not available on PATH.
**Options:**
- A. Replace the current dashboard with a new FastAPI + Next.js + custom control plane.
- B. Keep Hermes as the control plane and add Army Operations as an additive War Room module.
- C. Wait for Codex CLI before implementing anything.
**Decision:** Option B.
**Rationale:** The existing dashboard already has the correct plugin/backend/frontend shell and profile-safe overlay rules. Replacing it would violate the user's no-bulldozing rule and risk losing current panels. Codex can be represented as unavailable until installed; Claude Code is the available v1 worker.
**Council:** Claude Boss reviewed and required: no `shell=True`, run state store, safe identifiers, path confinement, log scrubbing, rate limits, no profile mutation, and explicit gates.
**Safety Gate:** v1 approve marks a run approved but does not merge, push, or mutate profiles. All Army APIs must expose `writes_profile_configs: false` where relevant.

---
END OF LOG
