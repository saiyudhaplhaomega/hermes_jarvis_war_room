# Getting Started — Hermes Jarvis War Room

> Created 2026-06-08. If something is broken after a fresh boot, this is
> the document that will get you back to a running system.

## What you actually have

This repo (`C:\Users\saiyu\Desktop\projects\KI_projects\hermes_jarvis_war_room`)
is a self-hosted **multi-agent dashboard** for an "AI company army":

- **FastAPI backend** at `http://127.0.0.1:8502` — 60+ endpoints, SQLite-backed
- **React 19 frontend** at `http://127.0.0.1:5173` — 19+ panels including
  Topology Editor, Army Operations, Agent Growth Studio, Discord Nexus
- **13+ named agents** in a hierarchy: boss → manager → 5 leads → scouts
- **Hindsight memory server** (Docker) at `http://127.0.0.1:18888` — live
- **Ollama** at `http://127.0.0.1:11434` — 3 models loaded
- **n8n** (Docker) at `http://127.0.0.1:5678` — workflow automation

**`***` works fine.** Hindsight doesn't validate the key — it
just passes it as the `Authorization: Bearer` header to the LLM
endpoint. When you point it at **ollama** (which is what we did, via
`HINDSIGHT_API_LLM_BASE_URL=http://host.docker.internal:11434/v1`),
ollama **ignores the Authorization header entirely**. Ollama is a local
server with no auth — it accepts any request.

So any non-empty placeholder string (`***`, `***`, `not-a-real-key`)
behaves identically. You only need a real key if you ever switch
`HINDSIGHT_API_LLM_BASE_URL` to a real OpenAI/Anthropic endpoint.

## ⚠️ PowerShell gotcha #1 — line continuations

**This WILL fail in PowerShell:**

```powershell
docker run -d --name hindsight -p 18888:8888 --restart unless-stopped \
  -e HINDSIGHT_API_LLM_API_KEY=*** \
  -e HINDSIGHT_API_LLM_BASE_URL=http://host.docker.internal:11434/v1 \
  ghcr.io/vectorize-io/hindsight:latest
```

You get: `docker: invalid reference format`

PowerShell treats `\` at the end of a line as a **path separator**, not a
line continuation. It silently mangles the command.

**Use one of these instead (both work in PowerShell):**

#### Option A — single line, no continuations

```powershell
docker run -d --name hindsight -p 18888:8888 -p 19999:9999 --restart unless-stopped -e HINDSIGHT_API_LLM_API_KEY=*** -e HINDSIGHT_API_LLM_BASE_URL=http://host.docker.internal:11434/v1 -e HINDSIGHT_API_LLM_MODEL=qwen2.5:7b-instruct -e HINDSIGHT_API_EMBEDDINGS_BASE_URL=http://host.docker.internal:11434/v1 -e HINDSIGHT_API_EMBEDDINGS_MODEL=nomic-embed-text ghcr.io/vectorize-io/hindsight:latest
```

#### Option B — PowerShell's native line continuation with backtick

```powershell
docker run -d --name hindsight `
  -p 18888:8888 -p 19999:9999 `
  --restart unless-stopped `
  -e HINDSIGHT_API_LLM_API_KEY=*** `
  -e HINDSIGHT_API_LLM_BASE_URL=http://host.docker.internal:11434/v1 `
  -e HINDSIGHT_API_LLM_MODEL=qwen2.5:7b-instruct `
  -e HINDSIGHT_API_EMBEDDINGS_BASE_URL=http://host.docker.internal:11434/v1 `
  -e HINDSIGHT_API_EMBEDDINGS_MODEL=nomic-embed-text `
  ghcr.io/vectorize-io/hindsight:latest
```

> **The backtick `` ` `` is PowerShell's escape/continuation character.
> It is NOT a backslash.** If you paste bash-style `\` continuations into
> PowerShell, you get exactly the error you just hit.

#### Option C — run it in bash (easiest)

If you have Git Bash installed (you do), open **Git Bash** and the bash
version of the command works exactly as written in the docs.

```bash
docker run -d --name hindsight -p 18888:8888 -p 19999:9999 --restart unless-stopped \
  -e HINDSIGHT_API_LLM_API_KEY=*** \
  -e HINDSIGHT_API_LLM_BASE_URL=http://host.docker.internal:11434/v1 \
  -e HINDSIGHT_API_LLM_MODEL=qwen2.5:7b-instruct \
  -e HINDSIGHT_API_EMBEDDINGS_BASE_URL=http://host.docker.internal:11434/v1 \
  -e HINDSIGHT_API_EMBEDDINGS_MODEL=nomic-embed-text \
  ghcr.io/vectorize-io/hindsight:latest
```

## Hardware constraints (RTX 4070 laptop, 8 GB VRAM, 16 GB RAM)

You can run at most **one 7B model + a few small models simultaneously**.

| Model | Size on disk | VRAM | Status |
|---|---|---|---|
| qwen2.5:3b-instruct | 1.9 GB | 1.9 GB | Loaded by default |
| qwen2.5:7b-instruct | 4.7 GB | 4.7 GB | Council voice A (load on demand) |
| nomic-embed-text | 274 MB | 274 MB | Embeddings, always loaded |
| **Total peak** | **6.9 GB** | **~6.5 GB** | ~1.5 GB VRAM headroom |

**Do not pull additional models** (e.g. llava for vision, llama3 70B,
mixtral 8x7B) without checking VRAM first with `ollama ps`.

## Start order (do these in sequence)

### 1. Start Docker Desktop

Open **Docker Desktop** and wait for the whale icon in the system tray
to stop animating. First start after a reboot takes ~30s. The CLI won't
work until the daemon is up.

```powershell
docker info    # Should NOT say "Cannot connect to the Docker daemon"
```

### 2. Make sure ollama is running

```powershell
ollama --version
ollama list    # Should show 3 models (qwen2.5:3b, qwen2.5:7b, nomic-embed-text)
```

If ollama isn't running, start it as a background service or run
`ollama serve` in a separate terminal.

### 3. Start Hindsight (Docker)

```powershell
# Use Option A (single line) if you want to paste into PowerShell:
docker run -d --name hindsight -p 18888:8888 -p 19999:9999 --restart unless-stopped -e HINDSIGHT_API_LLM_API_KEY=*** -e HINDSIGHT_API_LLM_BASE_URL=http://host.docker.internal:11434/v1 -e HINDSIGHT_API_LLM_MODEL=qwen2.5:7b-instruct -e HINDSIGHT_API_EMBEDDINGS_BASE_URL=http://host.docker.internal:11434/v1 -e HINDSIGHT_API_EMBEDDINGS_MODEL=nomic-embed-text ghcr.io/vectorize-io/hindsight:latest
```

Wait ~20 seconds for it to come up, then verify:

```powershell
curl http://127.0.0.1:18888/health
# Expected: {"status":"healthy","database":"connected"}
```

**If it crashes with "LLM API key required"**: ollama isn't reachable
from Docker. The `host.docker.internal` DNS resolves to your host's
localhost. Make sure ollama is listening on `0.0.0.0:11434`, not just
`127.0.0.1:11434` (most installations default to all interfaces, so
this should work out of the box).

### 4. Start the FastAPI backend

```bash
# Use Git Bash, or PowerShell — both work for this one.
cd "C:/Users/saiyu/Desktop/projects/KI_projects/hermes_jarvis_war_room"
source venv/Scripts/activate   # bash
# or:  venv\Scripts\Activate.ps1   # PowerShell
uvicorn server:app --reload --port 8502
```

Verify:

```powershell
curl http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1/health
curl http://127.0.0.1:8502/api/plugins/jarvis-dashboard/v1/companies/jarvis-war-room/topology?token=dev
```

### 5. Start the React frontend

```bash
cd "C:/Users/saiyu/Desktop/projects/KI_projects/hermes_jarvis_war_room/frontend-react"
npm install    # first time only
npm run dev
```

Open `http://127.0.0.1:5173` in your browser.

### 6. Verify the full stack

Run the test suite from the project root:

```bash
cd "C:/Users/saiyu/Desktop/projects/KI_projects/hermes_jarvis_war_room"
venv/Scripts/python -m pytest tests/ -q
```

**Expected output:** `92 passed, 6 failed` — the 6 failures are
pre-existing in `test_agent_growth_api.py` and `test_release_quality_phase3.py`
and are unrelated to anything shipped in this session.

The `test_hindsight_live.py` tests will **skip** if Hindsight is not
running; they will **pass** if it is.

## What if Hindsight was already started in a previous session?

It will still be running (we used `--restart unless-stopped`). Verify:

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

You should see a row for `hindsight` with the two port mappings.

To stop it (frees ~500 MB RAM but loses the in-memory state):

```powershell
docker stop hindsight
```

To start it again:

```powershell
docker start hindsight
```

To wipe it clean (deletes the embedded PostgreSQL too):

```powershell
docker rm -f hindsight
```

Then re-run the `docker run` command from Step 3.

## Common issues

### "Cannot connect to the Docker daemon"
Docker Desktop is not running. Open it and wait for the whale icon to settle.

### "port is already allocated"
Something else is using 18888. Run:
```powershell
netstat -ano | findstr :18888
```
Find the PID, then `taskkill /PID <pid> /F`.

### "image not found: ghcr.io/vectorize-io/hindsight:latest"
You need to pull it first:
```powershell
docker pull ghcr.io/vectorize-io/hindsight:latest
```

### Tests fail with "module 'jarvis_company_os.registry' has no attribute 'KANBAN_DB_PATH'"
You have stale code. The fix in `registry.py` uses `registry._resolve_paths()`
(env-var-driven). Restart your Python kernel / uvicorn process.

### The frontend shows "Failed to fetch topology"
The backend isn't running, or the API URL is wrong. Check
`frontend-react/src/utils/config.ts` for the `API_BASE_URL`.

## Where to look when things break

| What broke | File to read first |
|---|---|
| Backend API | `backend/jarvis_company_os/router.py` |
| Topology editor | `backend/jarvis_company_os/registry.py` |
| Memory not saving | `backend/core/memory_router.py` (check `stats()` first) |
| Council not voting | `backend/core/council.py` |
| WebSocket disconnecting | `backend/core/websocket.py` |
| Frontend crash | browser DevTools console (F12) |
| Hindsight down | `docker logs hindsight --tail 50` |
| Ollama slow | `ollama ps` to see what's loaded |

## Useful aliases (add to your PowerShell profile)

```powershell
# Add to $PROFILE:
function wr-backend { Set-Location "C:\Users\saiyu\Desktop\projects\KI_projects\hermes_jarvis_war_room"; & ".\venv\Scripts\python.exe" -m uvicorn server:app --reload --port 8502 }
function wr-frontend { Set-Location "C:\Users\saiyu\Desktop\projects\KI_projects\hermes_jarvis_war_room\frontend-react"; npm run dev }
function wr-hindsight-start { docker start hindsight }
function wr-hindsight-stop { docker stop hindsight }
function wr-hindsight-status { curl http://127.0.0.1:18888/health }
function wr-test { Set-Location "C:\Users\saiyu\Desktop\projects\KI_projects\hermes_jarvis_war_room"; & ".\venv\Scripts\python.exe" -m pytest tests/ -q }
```

After saving the profile, reload it with `. $PROFILE`, then you can
just type `wr-backend` or `wr-test` from anywhere.

## What was built this session (so you know what's new)

- **Phase A** — Topology editor v1 (read + write endpoints with cycle
  detection, plus a 2D xyflow + dagre React component with an error
  boundary fallback)
- **Phase B** — Memory M1 router (routes facts to mem0, state to
  Hindsight, with a JSONL fallback for offline use)
- **Phase C** — Council 3-stage (karpathy/llm-council pattern) live-tested
  with codex + ollama qwen2.5:7b
- **Phase D** — 6-department starter kit (engineering, research, marketing,
  finance-ops, product, security) + management protocol + skills marketplace
  with 8 skills in a `registry.json`
- **Phase E** — WebSocket snapshot+delta with versioning + heartbeat + resync,
  Observability layer (Langfuse + JSONL), topology sub-phase 3 (write endpoints
  with cycle detection, codex consulted for the DFS algorithm)
- **Phase F** — Hindsight Docker server live, memory router wired to it via
  MCP-over-HTTP, 4 new tests in `test_hindsight_live.py` that skip when
  Hindsight is down

## Research base (for context)

- `docs/RESEARCH_FINDINGS.md` — master synthesis of 5 loops × 10 rounds
  of council consultations (50 rounds total, codex + ollama qwen2.5:3b each)
- `docs/RESEARCH_LEDGER.md` — raw findings for every round
- `docs/research/loop-1-summary.md` — deep-dive on memory systems

These three files tell you **why** every decision was made.
