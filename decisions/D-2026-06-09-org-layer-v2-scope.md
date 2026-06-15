# Org Layer v2 Scope — Defaulted to Option A (2026-06-09)

Per the 20-round deep research at `docs/research/r01-r20.md` and the council verdict on r01 (78,575 tokens used), the user did not pick A/B/C/D in r04. The research defaulted to **Option A** (full codex recommendation) and ran rounds 5-20 against that scope.

This Decision Brief records the default and the rationale, so a later Saiyudh review can downsize to Option B or C without re-running research.

---

## Decision (defaulted, pending user override)

**Default scope:** v2 ships the full org layer per codex's Round 1 ranking:
1. Cross-cutting cadence / RACI / shared-memory (rounds 10-14)
2. Product Lead prioritization (round 6)
3. Engineering Lead PR gate with QA / Security / Docs as required lanes (rounds 5, 8, 9, 15)
4. SEO Lead (round 7) for public-surface discoverability
5. Workflows (rounds 15-18) for PR-merge, spec-to-ship, feedback loop, OKR cadence
6. 6-week build plan per r19

**Build order (r19):**
- Week 1: cross-cutting foundations (doc-graph migration, on-call file, R15 HMAC fix)
- Week 2: Lead tiers (QA, Engineering, Security, Docs, Product, SEO)
- Week 3: workflows (PR-to-merge, spec-to-ship, feedback loop)
- Week 4: observability + budgets (cadence, budgets, OKR dashboard)
- Week 5: hardening (file locking, circuit breakers, SLO alerting)
- Week 6: close + handoff (OKR Q1 starts, retro, ongoing maintenance)

**BLOCKING risks for v2 launch (r19):**
- R1 — multi-worker uvicorn file races on JSON state. Mitigation: file-level locking.
- R7 — agent scope creep. Mitigation: written in/out-of-scope per lead.
- R15 — hardcoded HMAC secret in v1 discord_bridge. Mitigation: env-var migration.
- R18 — Boss is SPOF for after-hours Sev1. Mitigation: Boss + 1 backup rotation.

---

## Options (as in r04)

| Option | Scope | Effort | Defaulted? |
|---|---|---|---|
| A | Full codex recommendation: cross-cutting + Product + Engineering PR gate (with QA as sub-lane, Security/Docs/Ops as required gates) | 4-6 weeks | **YES (default)** |
| B | Cross-cutting + Product Lead only, no PR gate | 2-3 weeks | available on user override |
| C | Cross-cutting cadence only | 1-2 weeks | available on user override |
| D | Defer v2 entirely; continue hardening existing system | ongoing | available on user override |

---

## How the user can downsize

If the user wants Option B, C, or D, the v2-scope decision in this file can be overridden with a one-line edit + a new section appended. The downstream artifacts in `docs/research/r05-r20.md` remain valid for the cross-cutting rounds (10-14) and workflows (15-18); only the department specs (r05-r09) need re-scoping.

To override:
1. Edit this file, change the default from A to B/C/D
2. Append a "## User override YYYY-MM-DD" section
3. Re-scope rounds 5-9 against the new option (cross-cutting rounds and workflows are unchanged)
4. Update the implementation prompt (r20) build order

---

## References

- `docs/research/r01-org-primitives-recon.md` — recon (5.6 KB, real codex verdict)
- `docs/research/r04-v2-scope-decision.md` — the full A/B/C/D analysis
- `docs/research/r19-risk-register-sequencing.md` — 18 risks + 6-week build plan
- `docs/research/r20-implementation-prompt.md` — the single artifact the next session reads first
- `docs/research/DEEP_RESEARCH_BRIEF.md` — the original 20-round brief

---

## Status

**DEFAULTED TO OPTION A** — pending Saiyudh review. The implementation session is unblocked and can start against Option A. A user override to B/C/D is a 1-line edit to this file plus re-scoping of rounds 5-9.

**Decision class:** taste (per `decisions/classifier.md` — borderline mechanical since the default is "obvious" given the codex ranking, but Saiyudh's explicit override is required per the project's User-Challenge rule).
