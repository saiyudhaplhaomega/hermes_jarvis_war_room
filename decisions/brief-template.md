# Decision Brief Template (War Room / Jarvis)

Adapted from gstack deep dive. Used for any high-stakes clarify, council stop,
or spec gate. Keep the brief short enough that a tired operator can read it
in under 60 seconds.

## D-ID
- Format: `D-YYYY-MM-DD-<short-slug>`
- One per decision. Reuse the same D-ID when a decision is revised.

## Context
- 2 to 4 sentences.
- What is the current state and why is a decision needed now?

## ELI10
- 1 to 3 sentences. Explain it like the user just woke up and does not
  remember the project.

## Stakes
- What goes wrong if we pick wrong? What is the blast radius?
- Project scope vs global/company scope. Global/company scope must be
  explicitly approved by Saiyudh.

## Recommendation
- A single concrete recommendation. If there is no clear pick, state that
  the question must be split before answering.

## Options
- 2 to 4 options. If a question has 5+ options, the **split-if-5+ rule**
  applies: the question is split into 2-3 batches so no option is silently
  dropped. Never truncate options to fit a UI limit.

## Risks
- For each option, list the top 1 to 3 risks. Note reversibility.

## Reversibility
- Easy to revert, recoverable, or irreversible? This drives whether we
  may auto-proceed (Easy + Mechanical) or must stop for Saiyudh
  (Irreversible, or any User Challenge).

## Acceptance
- A concrete, falsifiable condition that proves the decision worked.
  Includes the smoke test, security check, and observation note.
