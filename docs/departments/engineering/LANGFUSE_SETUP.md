"""Langfuse Cloud integration guide for War Room (D-2026-06-08-f, Phase F).

Per Loop 5 R2: Langfuse is the default observability layer. Self-hosted
Langfuse is heavy (5+ containers, 2+ GB images, postgres + minio + redis
+ clickhouse). For a single-laptop dev workflow, **Langfuse Cloud free
tier is $0 and zero-ops** — we ship that path now and document the
self-hosted path as a separate day-long project.

## Setup (5 minutes)

1. Sign up at https://cloud.langfuse.com (free tier: 50k events/mo)
2. Create a project
3. Copy the public key + secret key
4. Set env vars:
   ```bash
   export LANGFUSE_HOST=https://cloud.langfuse.com
   export LANGFUSE_PUBLIC_KEY=pk-lf-...
   export LANGFUSE_SECRET_KEY=sk-lf-...
   ```
5. Verify:
   ```python
   from core.observability import get_client
   print(get_client().stats())
   # {'langfuse_enabled': True, ...}
   ```

## Self-hosted (when you outgrow free tier)

1. Copy docker-compose.yml from https://github.com/langfuse/langfuse
2. Generate a real salt + encryption key:
   ```bash
   openssl rand -hex 32
   ```
3. Update the .env file with real secrets
4. `docker compose up -d`
5. The SDK code in `core/observability.py` works with no changes — it
   auto-detects the env vars.

## What we already shipped (in-process)

Even without Langfuse, the observability layer:
  - Writes every trace to `~/.hermes/state/observability/traces.jsonl`
  - Records start/end, events, scores, errors
  - Computes stats (total, scored, errored, avg_score)
  - Exposes a context manager `traced("op-name", metadata={...})`

So Phase F's "in-process observability" is **done**; this file just
documents the upgrade path to the Langfuse UI.
"""
