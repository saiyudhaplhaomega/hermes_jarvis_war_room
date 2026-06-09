---
name: codex-then-ollama
owner: research
maturity: stable
triggers: [draft, summarize, explain, default]
---

# Codex-then-Ollama Skill

Two-stage LLM call: codex (gpt-5.5) for first draft, ollama (qwen2.5:7b) for independent second opinion. **Cheaper and faster than the full 3-stage council.** Use for routine work where strategic alignment is not the question.

## When to use

- Trigger: any default LLM task (summarize, explain, draft, classify, extract)
- Trigger: NOT for strategic decisions (use `council-vote` instead)
- Trigger: NOT for high-stakes or irreversible actions

## How

1. Call codex with the prompt (timeout: 60s)
2. Call ollama with the **same** prompt (timeout: 30s, model: qwen2.5:7b-instruct)
3. If the responses are consistent (>70% semantic overlap on key claims), return the codex version
4. If they disagree, flag the disagreement and call a third time for the tiebreaker
5. Log the call to the audit trail (which model, what prompt hash, latency, agreement score)

## Output shape

```markdown
## Codex-then-Ollama Result

**Task:** (one-line description)
**Codex:** (response)
**Ollama:** (response)
**Agreement:** (high / partial / low)
**Verdict:** (use codex / use ollama / escalate to council / merge)
**Latency:** (ms)
```

## Anti-patterns

- Skipping the second call "to save time" — that's exactly when you need it most
- Treating the agreement score as truth (it measures overlap, not correctness)
- Using this skill for decisions that should go through `council-vote`
