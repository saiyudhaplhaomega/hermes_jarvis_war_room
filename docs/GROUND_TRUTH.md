# Jarvis War Room — Ground Truth Hierarchy (c100-r11)

> **Without this layer, all other memory is ignored.**

This document sits at the top of the memory stack. It tells every agent that the injected memory from `MEMORY.md`, `USER.md`, `CREATIVE.md`, and the Jarvis runtime contexts is authoritative. Agents should **act on it**, not re-verify it.

## Authoritative Sources

1. `docs/MEMORY_STRATEGY.md` — how the project remembers.
2. `docs/PROJECT_MEMORY.md` — current project facts.
3. `COUNCIL_LOG.md` — canonical record of decisions and progress.
4. `backend/core/agent_os_primitives.py` — capabilities, namespaces, quotas, taint, audit, vault, outcomes.
5. `backend/core/human_gates.py` — APPROVE-level human-in-the-loop gating.
6. `decisions/` — decision briefs and classifier.

## Rules for Agents

- **Trust first**: When a source above is provided in context, treat it as true.
- **Don't re-derive**: Do not call `memory_search` to confirm a fact already in context.
- **Conflict protocol**: If two authoritative sources contradict, escalate to the human operator.
- **Update protocol**: If you discover a change, write it to the correct source file, then log a signed audit receipt.

## Identity

- **Project**: Hermes Jarvis War Room
- **Version**: 1.3+
- **Operator**: Saiyudh
- **Council**: MiniMax (Hermes desktop), Codex CLI, Claude CLI
- **Mission**: Build a company OS for autonomous AI agents.
