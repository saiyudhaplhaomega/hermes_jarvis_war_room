# V2 Whole-Company AI Scope — Defaulted to Option B (2026-06-09)

Per the 40-round V2 deep research at `docs/research/r21-gap-recon-delta-map.md` through `docs/research/r60-v2-implementation-prompt.md` (40 individual round artifacts, ~268 KB total) and the V2 brief at `docs/research/DEEP_RESEARCH_BRIEF_V2.md`, the user did not pick A/B/C in `r25-scope-gate-options.md`. The research defaults to **Option B** (full GTM automation with human approval gates) and runs rounds 6-40 against that scope.

This Decision Brief records the V2 default and the rationale, so a later Saiyudh review can upsize to Option C (true whole-company autonomy) or downsize to Option A (internal-only, stop here) without re-running research.

---

## Decision (defaulted, pending user override)

**Default scope:** V2 ships the full GTM automation layer per codex's overall recommendation in r25:
1. **Demand Engine** (rounds 6-13): lead gen, content marketing, multi-channel (email + paid + social), brand/orchestration, demand-gen journey, demand-gen KPIs, marketing stack, demand-gen risk
2. **Revenue Workflow** (rounds 14-20): sales dept, pipeline/forecast, quote/contract/billing, sales stack, sales journey, sales risk, marketing→sales handoff
3. **Customer Operating Loop** (rounds 21-26): CS dept, support, feedback→product journey, community/devex, CS stack, CS risk
4. **Cross-cutting company layer** (rounds 32-35): operating ledger, KPI/forecasting layer, handoff protocol, permissions/audit matrix
5. **End-to-end simulations** (rounds 36-38): 3 full customer/revenue/board journeys run on paper
6. **Risk + close** (rounds 39-40): 30+ risk register with integration-point deep-dive, 12-week build plan, new implementation prompt

**Build order (per r25's recommendation, authoritative version in r59):** ~12 weeks. Phasing per r59's 12-week plan: **Weeks 1-2** scope freeze, system map, owner/RACI, canonical customer model, cross-cutting controls (operating ledger, KPI layer, handoff protocol, permissions matrix). **Weeks 3-7** system integrations (HubSpot+Stripe sync W3, QuickBooks sync W4, Intercom routing W5, PostHog events W6, Slack alerts W7). **Weeks 8-10** GTM workflows + minimal finance/legal + permission tier tests. **Weeks 11-12** go-live rehearsal, manual fallback drills, production hardening + launch. r59's 12-week table is the single source of truth for the build order; this decision file is a summary only.

**BLOCKING risks for V2 launch (predicted per r25, confirmed at r59):**
- **R-INT-1** — external system downtime (HubSpot/Stripe/PostHog outage). Mitigation: operating ledger is the local cache; fail open with stale-data warnings.
- **R-LEGAL-1** — AI-generated contract exposure. Mitigation: human attorney approval on any non-standard term; AI redlines first-pass only.
- **R-FIN-1** — financial close errors. Mitigation: human CFO does the close; AI does 80% of the prep workpapers.
- **R-PERM-1** — human-only action bypass (refund, fire, sign contract, talk to press). Mitigation: permissions/audit matrix (r55) enforces the gate.

---

## Options (as in r25)

| Option | Scope | Effort | Defaulted? |
|---|---|---|---|
| A | Internal-product only (V1 20-round brief is the final deliverable) | 6 weeks (V1 r19) | available on user override |
| B | Full GTM automation: Marketing + Sales + CS, finance/legal minimally supported | **~12 weeks** | **YES (default)** |
| C | True whole-company autonomy: every dept, all 5 GTM primitives, full finance/legal/partnerships | 20-24 weeks | available on user override |

**Codex overall verdict (r25, 17,814 tokens):** "Choose B. It best matches 'lead generation, marketing' while still moving toward the larger 'AI-run company' goal without turning V2 into an overbuilt research artifact."

---

## What ships under Option B (the default)

- 14 new depts/workflows spec'd: Lead gen, Content, Multi-channel, Brand, Sales, Rev-ops, Quote/Contract/Billing, CS, Support, Community, Finance (AI-prep only), Legal (AI-redline only), Procurement, Partnerships (lite)
- 5 end-to-end journeys spec'd + 3 of them *simulated* on paper (lead-to-cash, feedback-loop, board-prep)
- The operating ledger as the cross-cutting source of truth for revenue/customer/state
- The KPI/forecasting layer tying every dept to business outcomes
- The handoff protocol defining every dept-to-dept transition
- The permissions/audit matrix preventing AI from doing human-only actions
- 30+ risks with integration-point deep-dive
- A 12-week build plan
- A new implementation prompt (r60) for the AI-run-company implementation session

## What does NOT ship under Option B (deliberately deferred, per codex)

- **Full finance/legal autonomy** (the dept is built; humans still do the close, redline non-standard contracts, approve exceptions)
- **Partnerships full program** (the spec is at r50 with a "defer to v3 if 6-month ARR < $500k" note)
- **Executive ops** (the Boss carries the executive-ops burden; v3 splits it)
- **All 5 GTM primitives at full depth** (primitive 1 Account Graph is full, primitives 2-4 are full, primitive 5 Business Control Plane is partial)

---

## How the user can override

If the user wants **Option A** (stop here, ship V1 only):
1. Edit this file, change the default from B to A
2. Append a "## User override YYYY-MM-DD" section
3. Cancel rounds 6-40 — the 22 existing V1 artifacts become the final research deliverable
4. Implementation session starts against V1 r20 instead of V2 r60

**If the user wants **Option C** (true whole-company autonomy, 20-24 weeks):**
1. Edit this file, change the default from B to C
2. Append a "## User override YYYY-MM-DD" section
3. Rounds 27-31 (company ops) expand from "skip or stub" to "full 5 depts" — finance becomes a full AI-prep+human-close workflow with rev-rec, legal becomes AI-first-pass+human-non-standard, partnerships becomes full program
4. Cross-cutting rounds (32-35) and simulations (36-38) don't change
5. Build plan extends from 12 to 20-24 weeks; the V2 r60 implementation prompt is rewritten to C-flavored

**If the user wants **Option D (sole-operator V2)** — added 2026-06-09 in response to "I am the only human" clarification:**
1. Edit this file, change the default from B to D
2. Append a "## User override YYYY-MM-DD: Option D" section
3. The scope is identical to B; only the **cost model** and **capacity model** change:
   - **Human cost: $0** (user is the sole operator)
   - **Tooling cost: $0/mo new incremental** (Codex + MiniMax + Claude Code Pro are all existing subscriptions, saiyudh.com owned, local Ollama/Nemotron self-hosted; or up to $260/mo if you turn on all optional paid tools like PandaDoc/lemlist/Plain, see `docs/research/COST_UPDATE_SOLE_OPERATOR.md`)
   - **$2000/mo cap: panic-button safety, not budgeted spend**
   - **Capacity multiplier: the 4 cross-cutting artifacts (r52-r55) — r52 ledger is the single source of truth, r53 KPI dashboard for daily review, r54 handoff protocol for self-service routing, r55 permissions matrix for the 5 AI-NEVER gates**
   - **R-CAPACITY-1 (sole-operator SPOF)** added to r59's risk register as a weekly-monitored meta-risk
4. Rounds 26-51 (dept specs) don't change in content; only the human-owner column in the RACI tables becomes "user (sole operator)" instead of "fractional operator"
5. Build plan stays at 12 weeks; the 80 new V2 tests and 311 total at launch don't change
6. Operating cadence: **daily 15-min dashboard + 1h exception review + monthly 4h close** (vs B's daily 1-2h per dept)
7. The implementation session reads the **ERRATA in r60** + **`COST_UPDATE_SOLE_OPERATOR.md`** first, then proceeds as B with the cost/owner updates

---

## References

- `docs/research/DEEP_RESEARCH_BRIEF_V2.md` — the 40-round brief (56 KB, 436 lines)
- `docs/research/r21-gap-recon-delta-map.md` — the 1-page delta map of the 20 V1 artifacts
- `docs/research/r22-external-systems-recon.md` — the 15 systems of record + v1/v2.1/v3+ split
- `docs/research/r23-ai-company-reference-model.md` — the 5 universal GTM primitives
- `docs/research/r24-journey-catalog.md` — the 5 end-to-end journeys
- `docs/research/r25-scope-gate-options.md` — the A/B/C analysis with codex verdict
- `docs/research/DEEP_RESEARCH_BRIEF.md` — the 20-round V1 brief (referenced, not re-derived)
- `decisions/D-2026-06-09-org-layer-v2-scope.md` — the V1 (internal-only) scope decision, still valid as the layer V2 extends

---

## Status

**DEFAULTED TO OPTION B** — pending Saiyudh review. The research session is unblocked and continues against Option B. A user override to A or C is a 1-line edit to this file plus the round 6-40 scope adjustments described above.

**Decision class:** taste (per `decisions/classifier.md` — borderline mechanical since the default is "obvious" given codex's overall verdict, but Saiyudh's explicit override is required per the project's User-Challenge rule).
