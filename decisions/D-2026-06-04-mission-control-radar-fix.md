# Decision — Mission Control Radar Fix (Taste)

Date: 2026-06-04
D-ID: D-2026-06-04-mission-control-radar-fix
Status: APPROVED by Saiyudh (option A)
Boss review: pending (Boss session rate-limited, re-routed)
Project: Jarvis War Room Dashboard

## Context

The rotating radar in `MissionControlOverview` is not centered and is
purely decorative. The dots are all the same color. The sweep is a 4s
linear constant with no signal. The user expects real activity with
status colors.

## Recommendation

Re-anchor the sweep to the center of the grid, and add per-status dot
colors. Keep the 4s linear rotation (no event-rate coupling).

## Status color map (no other styling change)

| status                                | color class           |
|---------------------------------------|-----------------------|
| online, active, running               | `radar-dot--online`   |
| idle, ready                           | `radar-dot--idle`     |
| error, offline, failed                | `radar-dot--error`    |
| unknown / no status                   | `radar-dot--unknown`  |

## Files I plan to touch (additive only)

- `frontend-react/src/components/MissionControlOverview.tsx`
  - Render a helper `<RadarDot status={...}>` that maps status to a
    className suffix.
  - Keep the existing layout, dot count, and the radar grid.
- `frontend-react/src/index.css`
  - Add `.radar-dot--online`, `.radar-dot--idle`, `.radar-dot--error`,
    `.radar-dot--unknown` rules (color + box-shadow only, no shape
    change).
  - Replace `.radar-sweep` rule with a centered version
    (`top: 50%; left: 50%; width: 50%; transform-origin: 0 0`).

## Tests I plan to add (no source removed)

- `frontend-react/src/components/MissionControlOverview.test.tsx`
  - status -> className mapping for the four buckets.
  - radar-sweep element is rendered.
  - radar dot count is capped at 10.

## Verify

- `cd frontend-react && npm run build`
- Visual smoke through the tunnel
  `https://courage-bigger-monthly-corn.trycloudflare.com/`
  (the SPA serves the built dist, so a refresh picks up changes).

## Reversibility

All changes are additive. The diff is one helper component in
MissionControlOverview and CSS class additions in index.css. Reverting
is `git revert` of the commit.

## Notes for Boss re-review

When Boss's session quota resets, this brief and the implementation
commit are linked so Boss can do a quick pass.
