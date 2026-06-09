# War Room Skills Marketplace

> D-2026-06-08-skills-marketplace. The single source of truth for what skills exist, who owns them, and when to use them.
> Per Loop 4 R6: separate `skills/*.md` files, lightweight registry, compatible with `npx skills add <repo>` pattern.

## How skills work

1. **Skills are markdown files with frontmatter.** Each lives in `docs/departments/skills/<name>.md`.
2. **The registry is `registry.json`.** It lists every skill, its triggers, required tools, and maturity.
3. **Composition strategy: pre-flight 2-3 + lazy activation.** The agent router picks the 2-3 most likely skills before the turn, then activates more on signal.
4. **Loading: NEVER inline a skill into SOUL.md.** SOUL.md gets a 1-line pointer like "load `skills/code-review.md` for PRs."

## How to add a new skill

1. Copy an existing skill as a template
2. Edit the frontmatter (name, owner, triggers, maturity)
3. Write the body (when to use, how, output shape, anti-patterns)
4. Add an entry to `registry.json`
5. Commit with `[D-2026-06-08] Add skill <name>`

## How to retire a skill

1. Move the file to `skills/_deprecated/`
2. Remove it from `registry.json`
3. Update any SOUL.md files that referenced it
4. Commit with `[D-2026-06-08] Deprecate skill <name>: <reason>`

## How to use a skill from code

```python
import json, pathlib
registry = json.loads(pathlib.Path("docs/departments/skills/registry.json").read_text())

def find_skills(query: str) -> list[dict]:
    """Pre-flight skill selection. Returns 2-3 most likely skills."""
    q = query.lower()
    scored = []
    for skill in registry["skills"]:
        score = sum(1 for t in skill["triggers"] if t.lower() in q)
        if score > 0:
            scored.append((score, skill))
    scored.sort(reverse=True)
    return [s for _, s in scored[:3]]
```

## How to use a skill from the agent

The agent's SOUL.md has a 1-line pointer:

```markdown
## Default skills (pre-flight)
- code-review (engineering)
- codex-then-ollama (research)

## On-demand skills (lazy activation)
- council-vote: triggered by "decide", "tradeoff", "architecture"
- incident-triage: triggered by "incident", "outage", "down"
```

When the user message contains a trigger, the agent loads the full skill markdown on the fly.

## Current skills

See `registry.json`. As of 2026-06-08:

| Name | Owner | Maturity | Triggers |
|---|---|---|---|
| code-review | engineering | stable | review, pr, diff |
| perspective-guided-research | research | stable | research, investigate, compare |
| incident-triage | finance-ops | stable | incident, outage, broken |
| codex-then-ollama | research | stable | draft, summarize, explain, default |
| council-vote | council | stable | decide, tradeoff, architecture |
| agent-soul-update | engineering | stable | change agent, update soul |
| memory-add-fact | research | stable | remember, save fact, store |
| memory-recall | research | stable | recall, what did we, do you remember |

## Anti-patterns

- **Inline skills in SOUL.md** — they become unreviewable, untestable, unversioned
- **No registry** — agents can't discover skills, and you can't audit which are stale
- **One skill per task** — pre-flight 2-3, not 1, gives the agent options
- **Skill sprawl** — if you have 50 skills, you need a categorization layer; if you have 5, you don't
