# Decision — Panel collapse scope + card shrink (Mechanical)

Date: 2026-06-04
D-ID: D-2026-06-04-panel-collapse-scope-and-shrink
Status: AWAITING Boss
Project: Jarvis War Room Dashboard

## Context

Saiyudh reported: "for some the entire content isnt collapsing like
the first one Agent growth studio, only the small items like storage,
safety contract are coollapsing. and the boxes or the container
should strink as well when it collapse but its not happening , its
consuming space. the idea for the collapse was to save space and
keep important things in view. and others are not collapsing at all"

I audited every collapsible panel, ran a live jsdom test against the
real components (panel-collapse-live.test.tsx) and got this verified
breakdown:

| Panel        | Direct siblings after header             | Body fully hidden? | Card shrinks? |
|--------------|------------------------------------------|--------------------|---------------|
| MemoryNexus  | 2 (scope line, list)                     | NO (only scope)    | NO            |
| DecisionLog  | 2 (scope line, list)                     | NO (only scope)    | NO            |
| CouncilChamber | 1 (list with footer nested inside)     | YES                | NO            |
| DiscordNexus | 1 (list)                                 | YES                | NO            |
| GitHubWorkspace | 1 (form)                              | YES                | NO            |
| AgentConstellation | 1 (grid)                          | YES                | NO            |
| KanbanFleet  | 1 (grid)                                 | YES                | NO            |
| RoleMatrix   | 3 (4-col cards, role table, growth grid) | NO (only 4-col)    | NO            |

Two real defects:

1. The CSS rule
     [data-panel-header].panel-collapsed + * { display: none; }
   only matches ONE sibling (the adjacent sibling combinator `+`).
   Panels with 2+ direct siblings after the header leave the rest
   visible.

2. The card has a min-height that does not collapse with its body:
     .premium-card { min-height: 280px; }
     .agent-growth-card { min-height: 620px; }
   So even when the body is fully hidden, the slot stays tall.

## Recommendation (Mechanical)

Two additive CSS changes in src/index.css, no panel file touched,
no PanelHeader.tsx change.

### Part 1: scope

Replace
  [data-panel-header].panel-collapsed + * { display: none; }
with
  [data-panel-header].panel-collapsed ~ * { display: none; }

The `~` general-sibling-combinator matches every following sibling.
Supported in every browser since IE9.

### Part 2: shrink

Add a new rule that drops the min-height when a card contains a
collapsed header. The `:has()` selector is the cleanest expression
of that intent:
  .card:has([data-panel-header].panel-collapsed),
  .premium-card:has([data-panel-header].panel-collapsed) {
    min-height: 0;
  }

`:has()` is supported in Chrome 105+ (Sep 2022), Firefox 121+
(Dec 2023), Safari 15.4+ (Mar 2022). All modern browsers.

Combined with the existing
  .dashboard-section > .card,
  .dashboard-section > .premium-card { height: 100%; }
the card will collapse to its header height (which is its own line
plus the 16px padding from .card).

## Files I plan to touch (additive only, no deletions)

- frontend-react/src/index.css: replace the `+` with `~`, add the
  `:has()` rule.

## Tests I plan to add (RED first, then GREEN)

panel-collapse-live.test.tsx already exercises 8 panels with the
production rule. I will:

1. Change every "BROKEN" assertion to expect 0 visible siblings
   after collapse. MemoryNexus, DecisionLog, RoleMatrix.
2. Add 8 new assertions: after collapse, no `.card` or
   `.premium-card` may have a computed min-height equal to its
   pre-collapse min-height. (jsdom returns 0 by default, so the
   meaningful check is that the :has() rule is present in the
   source CSS and applies the right cascade. We can verify the
   rule source via the existing beforeAll in PanelHeader.test.tsx
   + extend it.)
3. Add a regression-guard beforeAll that reads src/index.css and
   asserts both rules are present:
     - the `~` selector
     - the `:has()` selector

## Verify

- cd frontend-react && npm run build
- cd frontend-react && ./node_modules/.bin/vitest run
- cd .. && ./venv/bin/python -m pytest tests/ -q

## Reversibility

Two CSS lines. `git revert` of the single commit restores the prior
state.

## Risk

`:has()` requires modern browsers. The dashboard is a Vite SPA that
already requires a modern browser to run. The build does not target
old browsers. Acceptable.
