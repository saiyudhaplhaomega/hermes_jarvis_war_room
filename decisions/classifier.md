# Three-Class Decision Classifier (War Room / Jarvis)

Adapted from gstack's "Mechanical / Taste / User Challenge" classifier.
This is the only classifier used by Jarvis agents. Use it before any
auto-action or auto-fix.

## Mechanical
- Objective, deterministic, reversible.
- Examples: rename an unused import; add a missing type hint; format JSON.
- Approval: Boss + Manager agreement. No user stop required.
- Reminder: Mechanical does not mean "skip the brief" — large Mechanical
  changes still need a brief so the diff is reviewable.

## Taste
- Subjective, has a defensible default, reversible.
- Examples: pick a log message wording; choose between two equivalent UI
  layouts.
- Approval: Boss decides, Manager reviews, Boss final.
- Default to the option that is closer to existing project conventions.

## User Challenge
- Anything that crosses the user's authority, scope, taste, or risk
  tolerance, even if Boss+Manager agree.
- Examples: project vs global scope; permanent deletion; spending money;
  shipping to production; modifying another Hermes profile; exposing a
  new control surface; changing auth.
- **Hard-stop rule: never override Saiyudh. Boss+Manager cannot override
  the user on a User Challenge even with unanimous agreement.**
- Default action: stop and present the Decision Brief.
