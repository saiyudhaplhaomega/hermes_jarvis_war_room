---
name: memory-add-fact
owner: research
maturity: stable
triggers: [remember, save fact, store this, log this]
---

# Memory: Add Fact

Add a fact to the project memory bank. Auto-classifies trust tier. **Use the `memory_router.py` module.**

## Trust tiers (per existing `backend/core/memory.py`)

| Tier | When to use | Examples |
|---|---|---|
| `OBSERVED` | The system itself witnessed this (a tool call, a logged action) | "Boss approved run #42" |
| `USER_STATED` | The user explicitly told us this | "Saiyudh prefers dark mode" |
| `INFERRED` | We derived it from multiple sources, with reasoning | "User is probably a backend engineer" (based on tools they use) |
| `CROSS_MODEL` | Came from another model, lower trust | "Codex said the user wants X" |

## When to use

- Trigger: "remember this", "save that", "log this"
- Trigger: an automated system detects a noteworthy fact
- Trigger: end of any task that produced a decision or learning

## How

```python
from core.memory_router import MemoryRouter
router = MemoryRouter(project_id="jarvis-war-room")
router.add_fact("Saiyudh prefers dark mode", trust_tier="USER_STATED")
```

If `mem0` is installed and reachable, the fact is sent there. Otherwise, it falls back to a JSONL file at `~/.hermes/state/memory/<project>/factual.jsonl`.

## Output shape

A `MemoryItem` object with:
- `id` (UUID)
- `data_type` ("factual")
- `content` (the fact text)
- `trust_tier` (one of 4)
- `metadata` (dict, optional)
- `created_at` (timestamp)

## Anti-patterns

- Storing the same fact under multiple trust tiers (it'd be searched twice and look more important than it is)
- Storing opinions as facts (subjective claims need `INFERRED` tier, not `OBSERVED`)
- Storing without a project_id (everything is project-scoped per CLAUDE.md)
