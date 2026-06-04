# Decision — Radar "configured" tone + legend (Taste)

Date: 2026-06-04
D-ID: D-2026-06-04-radar-configured-tone
Status: APPROVED (Saiyudh, then Boss PASS)
Project: Jarvis War Room Dashboard

## Context

The Mission Control radar renders the first 10 agents. 10 of 11 live
agents have status `running` and 1 has status `configured` (declared
but not yet active). The radar tone mapping only knows online/active/
running, idle/ready, error/offline/failed/down; everything else falls
to `unknown` which renders grey. The user sees 9 green + 1 grey dot
and reads it as a bug. It is a real, common backend state — the radar
just has no color for it.

## Recommendation

Add a new `configured` tone covering `configured`, `pending`, `paused`,
`standby`, `disabled`. New CSS class `.radar-dot--configured` (indigo,
no pulse, dimmer than online). Add a small legend strip below the
radar so the five tones are interpretable.

## Status -> tone map (radar)

| input status                              | tone       | class                       | visual                          |
|-------------------------------------------|------------|-----------------------------|---------------------------------|
| online, active, running                   | online     | `radar-dot--online`         | emerald + 2.4s pulse            |
| idle, ready                               | idle       | `radar-dot--idle`           | cyan, soft glow                 |
| error, offline, failed, down              | error      | `radar-dot--error`          | red glow                        |
| configured, pending, paused, standby, disabled | configured | `radar-dot--configured`   | indigo, no pulse, dimmer        |
| (anything else)                           | unknown    | `radar-dot--unknown`        | muted gray                      |

The legend swatch label is **staged** (Boss's copy nit: the line-78
"X running / Y configured" summary uses "configured" to mean *total*;
calling the dot "staged" avoids ambiguity). Final legend: online /
idle / error / staged / unknown.

## Files I plan to touch (additive only, no deletions)

- `frontend-react/src/components/MissionControlOverview.tsx`
  - extend `toneForStatus()` to map the new statuses
  - new `<RadarLegend />` subcomponent rendered under the radar
  - new tests
- `frontend-react/src/index.css`
  - new `.radar-dot--configured` rule
  - new `.radar-legend` / `.radar-legend-swatch` rules

## Tests I plan to add

- `frontend-react/src/components/MissionControlOverview.test.tsx`
  - new tests: configured/pending/paused/standby/disabled -> configured
  - new test: legend renders 5 entries with the right labels
  - new test: typo status -> unknown (regression guard)

## Verify

- `cd frontend-react && npm run build`
- `cd frontend-react && ./node_modules/.bin/vitest run`
- Visual smoke through the trycloudflare URL after a hard browser
  refresh.

## Reversibility

All changes are additive. One commit on a new branch
`feat/ui-radar-configured-2026-06-04` based on
`feat/ui-radar-and-dropdowns-2026-06-04`. `git revert` is a single
step.
