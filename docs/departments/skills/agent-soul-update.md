---
name: agent-soul-update
owner: engineering
maturity: stable
triggers: [change agent, update soul, new behavior, agent role]
---

# Agent SOUL Update Skill

Edit an agent's SOUL.md (or HEARTBEAT.md, TOOLS.md, AGENTS.md) with a clear before/after diff, citing the new behavior.

## When to use

- Trigger: any change to what an agent does, says, or uses
- Trigger: adding a new sub-role to a department
- Trigger: retiring an agent

## How

1. Read the current SOUL.md (and the related files)
2. Identify what needs to change and why
3. Write a clear diff:
   - **Before:** (quote the current text)
   - **After:** (the new text)
   - **Why:** (the new behavior, with a reference to the decision brief or research that triggered it)
4. Update the file
5. If the change is significant (new role, new tools, new escalation), update the management protocol doc too
6. Commit with a message like: `[D-2026-06-08] Update jarvis-scout SOUL.md: add perspective-guided-research skill`

## Output shape

```markdown
## SOUL Update: <agent-id>

**Triggered by:** (decision brief, research, incident, user request)
**Files changed:**
- `path/to/SOUL.md` — (1-line description)

### Diff

**File:** `path/to/SOUL.md`

**Before:**
```markdown
(quoted lines)
```

**After:**
```markdown
(new lines)
```

### Cross-references
- (any related docs that should be updated too)
```

## Anti-patterns

- "Let me just rewrite the whole SOUL" — small, surgical edits preserve history
- Updating SOUL without updating the management protocol — protocol and souls drift
- Forgetting to commit — uncommitted soul changes are ghosts
