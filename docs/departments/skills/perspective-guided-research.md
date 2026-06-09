---
name: perspective-guided-research
owner: research
maturity: stable
triggers: [research, investigate, compare, evaluate, analyze]
---

# Perspective-Guided Research Skill

Apply STORM's multi-perspective questioning to a research question. **The default for any non-trivial research task.**

## Default perspectives

For any research task, generate answers from at least 3 of these perspectives:

- **Operator** — what does the person doing the work need to know?
- **Customer** — what does the end user care about?
- **Competitor** — what are the alternatives, and what do they do better/worse?
- **Regulator** — what rules apply, and where are the boundaries?
- **Security** — what could go wrong, and how do we know?
- **Cost** — what's the resource ask, in time, money, complexity?
- **Implementation** (technical topics) — how do we build it?
- **Maintenance** (technical topics) — who owns it long-term?

## When to use

- Trigger: "research", "investigate", "compare", "evaluate", "analyze"
- Trigger: any question that would take >5 minutes to answer with a single search
- Trigger: a question where the answer could change the roadmap

## How

1. Identify the question
2. Pick 3-5 perspectives from the list above (or add domain-specific ones)
3. For each perspective, generate:
   - The question that perspective would ask
   - The answer that perspective would give
   - The source(s) supporting the answer
4. Synthesize: where do perspectives agree? where do they disagree?
5. Output a brief with the consensus + the disagreements + a confidence level

## Output shape

```markdown
## Research: [topic]

**Question:** (the actual question)
**Confidence:** (low/med/high) + reasons

### Perspectives
- **Operator:** [answer, source]
- **Customer:** [answer, source]
- ...

### Consensus
- (where all perspectives agree)

### Disagreements
- (where perspectives diverge, with the minority position named)

### Recommendation
- (concrete next step, with the conditions that would change it)

### Sources
- [URL] — [tier 1-5]
```

## Anti-patterns

- One perspective = bias. Always use ≥3.
- "The research is done when I found one source" = not done. Verify with a second.
- Mixing confidence with certainty. "I'm 80% confident" ≠ "I know."
