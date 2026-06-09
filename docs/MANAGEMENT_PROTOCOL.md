# Management Protocol — War Room

> D-2026-06-08-management-protocol. Codifies how the 13+ agent org works.
> Per Loop 4 R4 finding: *"War Room has the org chart, but not the management protocol."*

## Decision rights per tier

| Tier | Can decide | Cannot decide |
|---|---|---|
| **Worker** (scout, researcher, operators) | Execute the assigned task, ask clarifying questions, log discoveries | Approve changes, change scope, escalate to manager directly (go via lead) |
| **Lead** (eng-lead, qa-lead, security-lead, docs-lead, product-lead) | Approve within-budget tasks, reject bad work, reassign within team, run retros | Approve cross-team work, change budgets, change roadmap |
| **Manager** (jarvis-manager) | Approve cross-team work, manage budgets, prioritize, run planning | Change strategy, approve new hires, change public messaging |
| **Boss** (jarvis-boss) | Approve strategic tradeoffs, accept new strategic direction, override anything | Override user (Saiyudh) on a User Challenge decision |

**Hard rule:** Boss+Manager cannot override Saiyudh on a User Challenge decision, even with unanimous agreement. (Per `CLAUDE.md` decision classifier.)

## Handoff schemas

### Worker → Lead
Format: a JSONL log entry with `{ts, agent_id, task_id, status, evidence_path, blockers}`.

Example: `{"ts": "2026-06-08T19:00:00Z", "agent_id": "jarvis-scout", "task_id": "D-2026-06-08-research-mirofish", "status": "done", "evidence_path": "docs/research/loop-2-summary.md", "blockers": []}`

### Lead → Manager
Same JSONL shape, with `status: "ready_for_review"` and a PR or document link.

### Manager → Boss
A short brief (3-5 sentences) with the decision needed, the options, the recommendation, and the deadline.

### Manager → User (Saiyudh)
A 1-sentence summary with a single yes/no or pick-from-N question. Never more.

## Escalation rules (per Loop 4 R8)

Escalate on **blocker or threshold breach**, not by default.

| From → To | Triggers |
|---|---|
| Worker → Lead | blocked, exceeded budget/time/risk limit, affects another tier's mandate |
| Lead → Manager | cross-lead coordination needed, budget concerns, deadline risk |
| Manager → Boss | strategic tradeoffs, major stake exposure, authority Manager cannot exercise |
| Manager → User (Saiyudh) | User Challenge, irreversible action, budget > $10/mo, public messaging change |

**Confidence is advisory, not a default escalation trigger.** `confidence < X` triggers a second-opinion review, not an automatic Boss escalation, unless paired with high stakes or irreversible impact.

## Task lifecycle states

```
draft → ready → in_progress → blocked → review → done → archived
                  ↑___________|
```

- `draft` — being written, can be deleted without ceremony
- `ready` — committed to next sprint, has acceptance criteria
- `in_progress` — someone is working on it
- `blocked` — work stopped, needs escalation
- `review` — submitted for peer review
- `done` — merged/shipped, evidence on record
- `archived` — older than 90 days, searchable but not active

## Success criteria per task type

| Type | "Done" looks like |
|---|---|
| Bug fix | Reproducer test added, fix applied, test passes, no regression in adjacent tests |
| Feature | Acceptance criteria all checked, demo path documented, user-facing change noted in CHANGELOG |
| Research | `SYNTHESES.md` entry with sources, confidence level, recommended action, reviewer |
| Incident | Service restored, INCIDENTS.md entry within 48h, followups have owners and deadlines |
| Doc | Reviewed by at least one peer from a different department |

## After-action learning loop

Every task that hits `done` triggers a 60-second review:

1. **What went well?** (Capture it, so we can repeat it)
2. **What went poorly?** (Capture it, so we can fix it)
3. **What was unexpected?** (Update the threat model / assumptions)
4. **What should we change?** (Action item with owner)

The answer goes into a JSONL file per department, append-only.

## Anti-patterns the protocol forbids

- **Bystander escalation** — escalating a problem to a tier that can't fix it
- **Late escalation** — waiting until a problem is unfixable before flagging it
- **Silent escalation** — escalating without telling the original owner
- **Hero work** — solving a problem alone when the right answer was to escalate
- **Process for process's sake** — adding ceremony that doesn't change the outcome
