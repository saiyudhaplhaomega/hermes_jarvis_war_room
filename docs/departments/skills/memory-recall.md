---
name: memory-recall
owner: research
maturity: stable
triggers: [recall, what did we, do you remember, find past]
---

# Memory: Recall

Query the memory bank. Returns up to N matching facts, sorted by relevance. **Use the `memory_router.py` module.**

## When to use

- Trigger: "what did we decide about X", "do you remember Y"
- Trigger: starting a new task that may have prior context
- Trigger: an agent needs historical context to make a good decision

## How

```python
from core.memory_router import MemoryRouter
router = MemoryRouter(project_id="jarvis-war-room")
results = router.recall_facts("topology editor", limit=5)
for hit in results:
    print(f"[{hit.trust_tier}] {hit.content}")
```

## Search behavior

- **With mem0 installed:** multi-signal retrieval (semantic + BM25 + entity matching, fused)
- **Without mem0 (JSONL fallback):** substring match, sorted by token overlap

## Output shape

A list of `MemoryItem` objects, each with:
- `id`, `data_type`, `content`, `trust_tier`, `metadata`, `created_at`

## Anti-patterns

- Calling recall without a project_id (cross-project leakage)
- Storing the same fact in multiple memory systems (the master decision matrix in `docs/research/loop-1-summary.md` says: one fact, one system)
- Recalling 100+ results when 5 would do (LLM context budget is real)
