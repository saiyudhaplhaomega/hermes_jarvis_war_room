# Live MiniMax M3 Scout Findings — VPS + War Room

Timestamp: 2026-06-03T21:47-22:00+08:00
Scope: VPS disk/RAM, War Room readiness/observability, roadmap/protected frontend contracts, and security/config posture.
Status: archived for planning only. No code, cleanup, service restart, firewall change, CORS change, WS-auth change, or runtime mutation was applied by this archive.

## Execution notes

The built-in `delegate_task` tool attempted to route the three scouts through `deepseek-v4-pro` and returned `unauthorized` for all three calls. Direct Hermes one-shot execution was then smoke-tested successfully against MiniMax M3:

`hermes --profile jarvis chat --provider ollama-cloud -m minimax-m3 -Q -q 'Return exactly: MINIMAX_M3_DIRECT_OK'`

Three direct MiniMax M3 scout outputs were produced:

- `/tmp/minimax-m3-war-room-scouts/live-20260603/scout1-readiness-observability.out`
- `/tmp/minimax-m3-war-room-scouts/live-20260603/scout2-roadmap-frontend-contracts.out`
- `/tmp/minimax-m3-war-room-scouts/live-20260603/scout3-security-config.out`

Boss reviewed the combined findings via `boss-claude-review`; Manager/Codex reviewed Boss's ruling and returned `NO_OBJECTIONS`.

## VPS disk snapshot

Live filesystem snapshot:

- Root filesystem: `/dev/vda2` ext4, 59G size, 24G used, 34G available, 42% used.
- Same-filesystem `du` for `/`: 22G from readable paths.
- Major readable top-level contributors:
  - `/home`: 12G
  - `/usr`: 5.2G
  - `/var`: 2.9G
  - `/boot`: 95M
  - `/tmp`: 13M

Major `/home/ubuntu` contributors:

- `/home/ubuntu/.hermes`: 5.3G
- `/home/ubuntu/.cache`: 3.7G
- `/home/ubuntu/.npm`: 1.5G
- `/home/ubuntu/freqtrade`: 1.4G
- `/home/ubuntu/.cache/camoufox`: 1.4G
- `/home/ubuntu/.cache/uv`: 1.2G
- `/home/ubuntu/.cache/ms-playwright`: 631M
- `/home/ubuntu/.npm/_cacache`: 1.3G

Major `/home/ubuntu/.hermes` contributors:

- `hermes-agent`: 2.8G
  - `venv`: 1.7G
  - `.git`: 449M
  - `web`: 295M
  - `ui-tui`: 243M
- `profiles`: 1.2G
  - `profiles/jarvis`: 729M
  - `profiles/jarvis/plugins/jarvis-dashboard`: 267M
  - `profiles/jarvis/plugins/jarvis-dashboard-v1-backup`: 76M
- `node`: 445M
- `state-snapshots`: 280M
- `sessions`: 100M

Major `/var` contributors:

- `/var/log/journal`: 1.6G; `journalctl --disk-usage` reported 1.5G.
- `/var/cache/apt`: 125M
- `/var/lib/apt/lists`: 189M
- `/var/lib/rancher`: 217M

## VPS RAM snapshot

Live memory snapshot:

- Total RAM: 3.6Gi
- Used RAM: 2.3Gi
- Free RAM: 108Mi
- Buff/cache: 1.4Gi
- Available RAM: 1.2Gi
- Swap: 1.9Gi total, 1.0Gi used, 936Mi free

Aggregated process memory by family:

| Family | Processes | RSS | Swap |
|---|---:|---:|---:|
| Hermes/Jarvis gateways + CLI | 14 | 1354.8 MiB | 602.1 MiB |
| k3s/Kubernetes/monitoring | 22 | 614.8 MiB | 42.6 MiB |
| LSP/Node language servers | 5 | 210.7 MiB | 328.9 MiB |
| War Room dashboard | 2 | 57.9 MiB | 14.6 MiB |
| journald | 1 | 55.7 MiB | 0.8 MiB |
| ollama server | 1 | 10.3 MiB | 4.7 MiB |

Top RSS processes included:

- `k3s-server`: ~355M RSS
- main Hermes gateway run: ~337M RSS
- interactive Hermes CLI session: ~266M RSS
- `tsserver`: ~151M RSS
- Jarvis lead gateways: roughly 50-112M RSS each

Interpretation: the RAM pressure is primarily the full Jarvis multi-gateway fleet plus k3s/monitoring, with LSP/node language servers contributing substantial swap. The War Room dashboard itself is not a major RAM consumer.

## Scout 1 — readiness, liveness, observability

Findings:

1. `/api/plugins/jarvis-dashboard/health` is liveness-only and returns `ok` unconditionally.
2. No separate readiness endpoint exists.
3. The aggregator thread has no exposed `last_success` / `last_error` heartbeat.
4. `_scan_kanban()` swallows exceptions and can silently return `{}`.
5. SPA/static service has no explicit `/_hc`, though `spa_server.py` already has a no-log branch for that path.
6. Backend uvicorn `--no-access-log` is correctly present in the systemd launch path and must remain enabled.
7. Any future readiness probe must use the War Room/user Kanban DB read-only, with a short timeout, and must not write to either Kanban DB.
8. Any future readiness probe must avoid rate-limit false negatives.

Boss priority: `_scan_kanban` silent failure plus missing readiness endpoint are operational risks because `/health` can say healthy while data is stale or broken.

## Scout 2 — roadmap and frontend contracts

Findings:

1. P0-P8 roadmap/ticker is not implemented in the product UI.
2. P0-P8 is currently a planning/scout candidate, not a canonical taxonomy in `spec.md`, `plan.md`, or `tasks.md`.
3. Protected DOM IDs are live and must not be renamed casually:
   - `kanban-board`
   - `project-select`
   - `chat-thread`
   - `nl-input`
   - `audit-stream`
4. Protected frontend modules are present:
   - `frontend/public/js/theater.js`
   - `frontend/public/js/dna-helix.js`
   - `frontend/public/js/three-constellation.js`
   - `frontend/public/js/websocket-client.js`
5. A roadmap panel requires a spec-defined P0-P8 taxonomy before UI or endpoint work begins.

Boss/Manager ruling: do not start roadmap UI work until the P0-P8 taxonomy is written and approved.

## Scout 3 — security/config posture

Findings:

1. Service drift risk: the plugin tree includes a dashboard backend service file that binds `0.0.0.0:8502`, while the current production systemd path binds `127.0.0.1:8502`.
2. Live verification showed ports 8502 and 8503 currently listen only on `127.0.0.1`; there was no active public 8502/8503 exposure at verification time.
3. `backend/server.py`'s direct `uvicorn.run()` path does not explicitly disable access logs. The production systemd command does use `--no-access-log`.
4. CORS allowlist includes `http://43.131.26.109:8503` with `allow_credentials=True`; Boss flagged this as a top security item before any future deploy/public exposure.
5. JWT secret file exists at `/home/ubuntu/.hermes/state/dashboard/secret.key`, mode `600`; backup/restore behavior is not documented.
6. WebSocket auth still uses `?token=` query parameter as a known v1 risk.
7. Audit log exists at `/home/ubuntu/.hermes/state/audit/audit.jsonl`, about 633KB at inspection time, with no documented rotation/retention policy.

Boss priority: CORS/public-origin credential posture and WS `?token=` must be treated as security items before any release/public exposure. The 0.0.0.0 service file is a latent drift risk even though live sockets are loopback now.

## Boss/Manager ruling

Boss ranked the top issues:

1. CORS `allow_credentials=True` plus public IP in allowlist.
2. WebSocket `?token=` query parameter.
3. `_scan_kanban` silent exception handling and missing aggregator heartbeat.
4. No readiness endpoint.
5. Audit log has no rotation policy.

Manager reviewed Boss's ruling and returned `NO_OBJECTIONS`.

Safe documentation updates allowed now:

- Document `--no-access-log` as intentional.
- Document JWT secret path, permissions, and lack of backup guidance.
- Document current port binding: 8502/8503 are loopback-only at verification time.
- Document audit log path/current size and missing rotation policy.

Requires separate approval/spec before code or runtime changes:

- P0-P8 roadmap taxonomy and ticker.
- Readiness endpoint contract and implementation.
- WebSocket auth migration away from query token.
- CORS allowlist remediation.
- Audit log rotation implementation and retention policy.
- Any cleanup of `.cache`, `.npm`, journals, Hermes runtime files, k3s, LSP servers, or gateway processes.

## Guardrail

This archive is evidence and planning memory only. It does not authorize cleanup, process kills, service restarts, firewall changes, CORS changes, token/auth changes, or UI/API implementation.
