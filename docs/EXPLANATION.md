# War Room — Explanation

Diataxis category: **explanation** (background, reasoning, alternatives).

## Why IRON LAW exists
Confidence that "it works" is not evidence. Releases can be claimed on
stale test runs if timestamps are not compared to source mtimes. The
fresh-evidence gate forces a re-run when any source file was touched
after the last test run, preventing regressions from being claimed as
green.

## Why the route policy is an exact set
Allowlists work best when they are exhaustive and exact. A "contains"
check would silently accept new routes; an exact-set check forces
deliberate review of every addition.

## Why the User Challenge is a hard stop
The classifier exists to prevent the agent system from overstepping on
matters of scope, taste, or risk tolerance. Even unanimous Boss+Manager
agreement does not authorize overriding the user on a User Challenge.

## Why scoped per-agent tokens are deferred
The current design notes only design intent. Implementation introduces
a new control surface and a new failure mode (token revocation). Until
that surface is explicitly approved, we keep the dev token model.
