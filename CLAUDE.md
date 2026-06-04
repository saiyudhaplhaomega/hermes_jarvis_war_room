# Jarvis War Room — Repo Guidance (CLAUDE.md)

Adapted from gstack's `AGENTS.md` patterns. This file is the operating
manual for any agent touching this repo.

## Default workflow
1. Read the relevant spec under `decisions/` first.
2. If a Decision Brief is required, write one before coding.
3. Add failing tests first (RED). Then implement to GREEN.
4. Run the full test suite, not just the targeted test.
5. Update the spec/tutorial when behavior changes.

## Decision classifier
Use the three-class classifier in `decisions/classifier.md`:
- Mechanical
- Taste
- User Challenge

**User Challenge is a hard stop. Boss+Manager cannot override Saiyudh.
Never override Saiyudh on a User Challenge even with unanimous
agreement.**

## AskUserQuestion — split-if-5+ rule
If a question would have 5+ options, split it into batches of 2-4
options. Never silently drop or truncate options.

## Pre-emit verification gate
A review finding must include:
- the exact `file:line` reference, and
- the exact quoted text from that line that motivates the finding.

Findings without a quoted motivating line are suppressed and marked
`UNVERIFIED`. Boss has final say on contested findings.

## Project scope
Default scope is project-scoped. Global/company scope requires explicit
Saiyudh approval.

## File map
- `backend/` — FastAPI service.
- `frontend-react/` — Vite + React SPA.
- `spa_server.py` — static SPA server.
- `decisions/` — Decision Briefs, classifier, schemas.
- `tests/` — pytest suite.
- `ops/` — deployment, logrotate, systemd units.
- `docs/` — design and architecture docs.
