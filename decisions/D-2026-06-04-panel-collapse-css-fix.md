# Decision — Panel collapse CSS selector fix (Mechanical/Taste)

Date: 2026-06-04
D-ID: D-2026-06-04-panel-collapse-css-fix
Status: APPROVED (Saiyudh, then Boss CONDITIONAL PASS with 2 blockers)
Project: Jarvis War Room Dashboard

## Context

Saiyudh reported "i can see you added the drop down buttons but they
are not collapsable". Investigation: the collapsible panel headers
shipped in commit 58e67dd. The toggle works (aria-expanded flips,
the icon rotates, the data attribute is set), but the body never
disappears. Cause: index.css line 405 has

    .panel-collapsed + .panel-body { display: none; }

None of the 8 panel files render their body with class "panel-body".
Their next siblings are <div className="text-[10px]"> or
className="space-y-2 max-h-[300px]"> etc. So the selector matches
nothing and the body stays visible.

## Recommendation

Replace the specific selector with a generic one that hides whatever
sibling comes after the wrapper, without changing any panel file:

    [data-panel-header].panel-collapsed + * { display: none; }

This works in all modern browsers. No code change to PanelHeader.tsx
(useState logic is correct). No change to any of the 8 panel files.
Boss confirmed this as the correct minimal fix.

## Boss blockers

1. The CSS fix must actually be applied (it is not yet).
2. A real sibling-hiding test must be added to PanelHeader.test.tsx.
   The "rule exists in src/index.css" smoke test is acceptable as
   regression guard but must be paired with at least one DOM-level
   assertion that confirms the next sibling is hidden after collapse.

## Files I plan to touch (additive only, no deletions)

- frontend-react/src/index.css: change one selector.
- frontend-react/src/components/PanelHeader.test.tsx: add two tests.

## Tests I plan to add

In PanelHeader.test.tsx, add:
- 'hides the next sibling when collapsed' (DOM-level via real CSS):
  render <div><PanelHeader title="X" collapsible /><div
  data-testid="body">body</div></div>, click toggle, assert that
  the body's computed display is 'none' after a layout flush.
  Implementation: read the actual rule from src/index.css (string
  match) and apply it to a <style> tag in the test, then assert.
- 'keeps the next sibling visible by default' (regression guard):
  render same, assert body's computed display is not 'none' before
  any click.

## Verify

- cd frontend-react && npm run build
- cd frontend-react && ./node_modules/.bin/vitest run
- cd .. && ./venv/bin/python -m pytest tests/ -q

## Reversibility

One CSS selector change and two new test cases. `git revert` of the
single commit restores the prior state.
