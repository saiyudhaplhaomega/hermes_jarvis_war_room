# Scoped Per-Agent Token — Design Only

Status: design only. Implementation remains separately gated.
Source: gstack deep dive → War Room adaptation plan.

## Why
Today every agent shares the same dev/JWT token. That makes blast-radius
control and per-agent audit impossible.

## Goals
- One short-lived token per agent run.
- Token has a narrow scope: allowed routes, allowed actions, time-bound.
- Token never appears in URLs.
- Token never appears in logs, Obsidian, or memory.

## Non-Goals (this phase)
- No implementation. No code, no migration, no test scaffolding beyond
  design acceptance criteria.
- No revocation protocol — out of scope until Phase 3 release gate.

## Proposed shape
- Mint: `/v1/admin/issue-agent-token` (admin-only).
- Claims: `agent_id`, `scopes[]`, `routes[]`, `iat`, `exp`, `jti`.
- Transport: HttpOnly cookie set by `/sse-session` style bootstrap, or
  in-memory only for non-browser agents.
- Storage: never on disk in plaintext. Memory only, process-scoped.

## Acceptance (for future implementation phase)
- A leaked token cannot reach a non-allowed route.
- A leaked token cannot authenticate to a new agent context.
- All denied attempts appear in the same redacted denial log.
- Tokens never appear in access logs, Obsidian, or memory.
