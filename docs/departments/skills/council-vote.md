---
name: council-vote
owner: council
maturity: stable
triggers: [decide, tradeoff, architecture, should we, which one]
---

# Council Vote Skill

Run a 3-stage council vote (parallel → anonymized rank → chairman). **Reserve for strategic decisions.** For routine work, use `codex-then-ollama` instead.

## The 3 stages (per karpathy/llm-council)

### Stage 1: parallel independent
Each model gets the question alone. No model sees another's response. Their answers are collected.

### Stage 2: anonymized ranking
Each model sees the other responses with anonymous labels (resp_0, resp_1, ...). They rank by:
- correctness (is the claim true?)
- risk-awareness (does it flag the dangers?)
- completeness (does it cover the full question?)
- actionability (does it tell us what to do?)

### Stage 3: chairman synthesis
The chairman (default: codex, the strongest model) sees everything: the question, all stage-1 responses, all stage-2 rankings. They write the final answer. **Minority warnings must be preserved** — never average them out.

## When to use

- Trigger: strategic decision (architecture, security policy, public messaging)
- Trigger: irreversible action (delete data, change billing, change public API)
- Trigger: high-stakes tradeoffs (build vs buy, ship vs wait)
- **NOT** for routine work (use `codex-then-ollama`)

## How

Use the council module (Loop 3 R1 implementation):

```python
from core.council import Council
c = Council(models=["codex", "ollama:qwen2.5:7b-instruct"], chairman="codex")
decision = c.run("Should we adopt Graphiti for temporal memory? Yes/no + 2 sentence why.")
print(decision.stage3_synthesis)
print("Minority warnings:", decision.minority_warnings)
```

## Cost & latency

- 5 LLM calls per decision (2 stage-1 + 2 stage-2 + 1 stage-3)
- ~60-120s total
- ~10-20k tokens

Reserve for: ~1-5 decisions per day, not hundreds.

## Output shape

A `CouncilDecision` object with:
- `stage1_responses` (dict of anon_id → response)
- `stage2_rankings` (list of ranking dicts)
- `stage3_synthesis` (the chairman's final answer)
- `minority_warnings` (list of strings, must be reviewed)
- `model_list` (which models participated)
- `chairman` (which model synthesized)
- `created_at` (timestamp)

Always log the full decision to the audit trail.

## Anti-patterns

- Using the council for everything (it's expensive and slow)
- Averaging or majority-voting stage-2 rankings (you lose the minority warnings)
- Letting the chairman skip the minority warnings in stage 3
- Running the council without logging (decisions without audit = nothing happened)
