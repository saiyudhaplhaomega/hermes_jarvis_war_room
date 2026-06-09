---
name: incident-triage
owner: finance-ops
maturity: stable
triggers: [incident, outage, broken, down, error spike]
---

# Incident Triage Skill

First 5 minutes of any incident. **Goal: scope, severity, and immediate mitigation. Root cause analysis is for AFTER the fire is out.**

## Severity scale

| Sev | Definition | Response time | Examples |
|---|---|---|---|
| 1 | Cosmetic | next business day | Typo, broken alignment |
| 2 | Annoying | within hours | Single feature broken, no workaround |
| 3 | User-impacting | within 30 min | Login broken, data not saving |
| 4 | Critical | within 5 min | Service down for multiple users, data loss risk |
| 5 | Catastrophic | immediate | Data breach, data loss, security event |

## When to use

- Trigger: "incident", "outage", "broken", "down", "error spike"
- Trigger: any PagerDuty / alertmanager alert (future)
- Trigger: any user report with severity ≥ 3

## How (the first 5 minutes)

1. **Confirm:** is this real? Check the dashboard, query a real metric, ask a second human/agent.
2. **Scope:** who/what is affected? One user, one feature, all users?
3. **Severity:** assign 1-5 using the table above.
4. **Mitigate:** can we stop the bleeding? (rollback, feature flag off, redirect traffic, take the service down)
5. **Communicate:** post a status update. Who's affected, what's broken, what we're doing, ETA if known.
6. **Escalate:** if severity ≥ 3, page the on-call manager. If severity ≥ 4, page the boss and saiyudh.

## After the fire is out (postmortem)

Within 48 hours, file an `INCIDENTS.md` entry with:
- Summary, root cause, resolution
- 5 whys (drill to systemic cause)
- Action items with owners + deadlines
- Disclosure status (for security incidents)

## Anti-patterns

- Jumping to root cause during triage (you'll waste time on the wrong thing)
- "I'll just fix it real quick" without mitigating first
- Communicating only after the fix (silence is worse than bad news)
- Skipping the postmortem because "we got it working"
