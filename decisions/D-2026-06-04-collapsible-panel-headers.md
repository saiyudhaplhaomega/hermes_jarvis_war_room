# Decision — Collapsible Panel Headers (Taste)

Date: 2026-06-04
D-ID: D-2026-06-04-collapsible-panel-headers
Status: APPROVED by Saiyudh (option A dropdowns)
Boss review: pending (Boss session rate-limited, re-routed)
Project: Jarvis War Room Dashboard

## Context

The dashboard has a fixed grid of 11 panels. All panels render in full
all the time. The user wants the major panels to be collapsible so
the screen is less crowded. The existing `PanelVisibilityProvider`
already hides whole panels through localStorage; collapse/expand is
independent of that and is per-panel state.

## Recommendation

Introduce a single shared `<CollapsiblePanelHeader />` (or extend
`PanelHeader` with an optional `collapsible` flag) that panels can
adopt. Default behavior is unchanged (no collapse). Apply to the
panels the user named:

- Agent Growth Studio (RoleMatrix)
- Skill Feed (sub-section inside RoleMatrix)
- Add Agent Proposal (sub-section inside RoleMatrix)
- Removed Agents (sub-section inside RoleMatrix)
- Kanban Fleet (KanbanFleet)
- Army Operations (ArmyOperations)
- Memory Nexus (MemoryNexus)
- Decision Log (DecisionLog)
- Discord Nexus (DiscordNexus)
- Council Chamber (CouncilChamber)
- GitHub Workspace (GitHubWorkspace)
- Agent Constellation (AgentConstellation)

## Files I plan to touch (additive only)

- `frontend-react/src/components/PanelHeader.tsx`
  - Accept optional `collapsible: boolean` and
    `onCollapsedChange?: (collapsed: boolean) => void`.
  - Default `collapsible: false` preserves existing behavior.
- `frontend-react/src/index.css`
  - `.panel-collapsed` hides the body, keeps the header.
  - `.panel-collapse-icon` rotates 0deg -> 90deg on toggle.
  - `.panel-header-toggle` for the click target.

## Tests I plan to add

- `frontend-react/src/components/PanelHeader.test.tsx`
  - default: not collapsible
  - when `collapsible: true`, body hidden via `aria-expanded` and the
    CSS class `panel-collapsed`
  - clicking the toggle flips the state

## Verify

- `cd frontend-react && npm run build`
- Visual smoke through the tunnel
  `https://courage-bigger-monthly-corn.trycloudflare.com/`
- Click-to-collapse on each of the listed panels

## Reversibility

All changes are additive. The default is `collapsible: false`, so any
panel that does not opt in keeps its current behavior. Reverting the
commit is a one-step `git revert`.

## Open question for Saiyudh

- Default state when a user first opens the dashboard: all collapsed,
  all expanded, or remember per panel in localStorage?

  Recommended: remember per panel in localStorage, default to expanded
  on first load. Matches the existing pattern (`STORAGE_KEY` for
  visibility).

## Notes for Boss re-review

When Boss's session quota resets, this brief and the implementation
commit are linked so Boss can do a quick pass.
