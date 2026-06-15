# /goal — War Room Company OS Improvement Sprint

Status: ACTIVE
Created: 2026-06-11
Owner: Jarvis
Project: Jarvis War Room Dashboard

## Goal

Run a no-stop improvement sprint over the Jarvis War Room so it becomes a stronger AI-company operating system for winning and delivering client projects. The sprint must find bugs, discover improvements from the broader internet/open-source ecosystem, use Claude CLI/MiniMax/Codex-style critique where available, and complete at least 30 concrete iterations before final synthesis.

## Boss Interpretation

`/goal` is treated as a project goal artifact, not as a Hermes slash command. Hermes Agent's loaded slash-command list does not include `/goal`, so Jarvis must not invent a hidden command. This file is the durable project-local goal record.

## Access/permission status

Preflight completed 2026-06-11:
- Project directory exists and is a git repo.
- Claude Code CLI is installed and authenticated.
- MiniMax settings are present in `~/.claude/settings.minimax.json`; use the settings file without exposing tokens.
- Codex CLI is installed.
- Node/npm, Python, curl, and network access are available.
- `gh` and `jq` were not present in PATH during preflight.
- Do not generate, persist, or use new real secrets/tokens without Saiyudh explicitly providing them.

## Constraints

- Preserve War Room project scope; do not mutate global Hermes profile configs unless Saiyudh explicitly asks.
- Respect active User Challenge decisions in `CLAUDE.md` and `decisions/`.
- No secret generation or persistence by the agent.
- Prefer additive docs/tests/code fixes over destructive rewrites.
- Use real tool output for every claim about tests, build, bugs, or access.
- When changing behavior, update docs/spec/tutorial as needed.

## Work Plan

1. Confirm access, toolchain, git state, and permission boundaries.
2. Read the active project guidance, prior research/decision artifacts, and feature inventory.
3. Run baseline backend/frontend quality gates and capture current failures.
4. Run internet/OSS research rounds focused on AI-company OS, agent workforce, project delivery, observability, memory, client acquisition, HITL, and workflow execution patterns.
5. Complete at least 30 improvement iterations. Each iteration records evidence, finding, action/recommendation, and verification.
6. Use Claude CLI with MiniMax settings and/or Codex for critique/brainstorming/review where practical.
7. Produce a final ranked roadmap, bug list, shipped patches, and verification summary.

## Completion Criteria

- Access/tool status recorded.
- Baseline tests/build/lint attempted with real output.
- Internet/OSS findings recorded in a sprint ledger.
- At least 30 iterations recorded.
- Bugs and improvements are grounded in file:line evidence or external research links.
- Final synthesis explains what changed, what remains, and the next highest-value implementation path.
