"""Discord gateway v2 (D-2026-06-09, Phase 3).

The dashboard-side of the user's locked Discord architecture:

    #coding_plan_feedback (1 channel) + per-project threads.

All 14 jarvis profiles can post to it. Each message is routed to a thread
that corresponds to the project slug. A JSON file maps
`project_slug -> thread_id` and is the source of truth on the dashboard
side. The actual HTTP call to Discord is a stub (see
`_dispatch_to_discord`) — Phase 4 will wire `discord.py`. Tests therefore
never reach out to the network.

**Load-bearing invariant:** this module does NOT touch Hermes profile
configs. Every response payload carries `writes_profile_configs: false`
and every code path that mutates state goes through the dashboard-side
JSON store only.

**Phase 5 hardening:** a module-level `_state_lock` (threading.Lock)
guards the entire read-modify-write transaction. `_mutate_state(fn)` is
the only sanctioned path for state changes — it acquires the lock,
reads, applies the caller-supplied mutation, writes back. This is
process-local; production must stay single-worker or add file-level
locking before scaling out.

**Phase 6 (r20):** Multi-guild support via `guild_map` (guild_id → agent_id).
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from core.config import DASHBOARD_DATA, PROFILE
from jarvis_company_os.registry import KNOWN_PROFILES as _REGISTRY_PROFILES
from auth.dependencies import get_current_user

router = APIRouter(prefix="/discord-gateway", tags=["discord-gateway"])
log = logging.getLogger("jarvis-discord-gateway")

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
# Env-var-overridable storage path, defaulting to the dashboard state dir.
# This matches the pattern at `api/agent_growth.py:28-31` for assignments
# and `:45-48` for the skill catalog.
STATE_FILE = Path(os.environ.get(
    "JARVIS_DISCORD_GATEWAY_STATE",
    str(DASHBOARD_DATA / "discord_gateway.json"),
)).expanduser()

# Slug-safe project ids: lowercase letters, digits, dashes, underscores,
# dots. Same shape as the `SAFE_NAME` regex at `agent_growth.py:27`.
SAFE_PROJECT = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")

WRITES_PROFILE_CONFIGS = False  # load-bearing invariant for every code path

# ---------------------------------------------------------------------------
# Multi-Guild Support (r20)
# ---------------------------------------------------------------------------
class DiscordGateway:
    def __init__(self):
        self.state_path = Path(DASHBOARD_DATA) / "discord_gateway_state.json"
        self._state_lock = threading.Lock()
        self._init_state()
        self.guild_map = {}  # guild_id → agent_id (multi-guild)
        self._init_guild_map()

    def _init_guild_map(self):
        """Initialize guild_map from environment or defaults."""
        guilds = os.environ.get("JARVIS_DISCORD_GUILD_MAP", "").strip()
        if guilds:
            for entry in guilds.split(","):
                guild_id, agent_id = entry.split(":")
                self.guild_map[guild_id] = agent_id

    def _init_state(self):
        if not STATE_FILE.exists():
            self._write_state({"threads": {}, "messages": []})

    def _write_state(self, state: dict) -> None:
        """Atomic write — same `tmp.replace` pattern as `agent_growth.py:194-198`.

        D-2026-06-09 (Phase 5): callers MUST hold `_state_lock` when calling
        this directly. The public mutation path is `_mutate_state(fn)`,
        which acquires the lock for the entire transaction.
        """
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(STATE_FILE.suffix + ".tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
        tmp.replace(STATE_FILE)

    def _mutate_state(self, fn: Callable[[dict], Optional[dict]]) -> Optional[dict]:
        """Read, mutate, write under a single lock. Returns the new state.

        D-2026-06-09 (Phase 5): the only sanctioned path for state
        mutations. Acquires `_state_lock`, reads, calls `fn(state)` to
        apply the caller's mutation (the caller may mutate in place or
        return a new dict), writes the (possibly new) state back, and
        returns whatever `fn` returned. The lock is released on exit
        even if the mutation raises.
        """
        with self._state_lock:
            state = self._read_state()
            result = fn(state)
            if result is not None:
                state = result
            self._write_state(state)
            return state

    def _read_state(self) -> dict:
        if not STATE_FILE.exists():
            return {"threads": {}, "messages": []}
        try:
            data = json.loads(STATE_FILE.read_text())
        except Exception:
            return {"threads": {}, "messages": []}
        if not isinstance(data, dict):
            return {"threads": {}, "messages": []}
        threads = data.get("threads")
        if not isinstance(threads, dict):
            threads = {}
        messages = data.get("messages")
        if not isinstance(messages, list):
            messages = []
        return {"threads": threads, "messages": messages}

    def _dispatch_to_discord(self, *, thread_id: str, profile: str, content: str, guild_id: str = None) -> None:
        """POST a message to Discord via the REST API (best-effort).

        Per the user-locked architecture, the dashboard JSON is the source
        of truth. Discord is a side channel. The gateway must continue to
        return success on the dashboard side regardless of Discord
        availability. All failures are logged with ids/sizes only — no
        message content is logged.
        """
        token = _discord_bot_token()
        if not token:
            log.info(
                "%s skip reason=no_token thread_id=%s profile=%s content_len=%d",
                _DISCORD_DISPATCH_LOG_PREFIX, thread_id, profile, len(content),
            )
            return
        
        # Multi-guild: route to the correct guild's channel
        channel_id = thread_id
        if guild_id and guild_id in self.guild_map:
            channel_id = f"{self.guild_map[guild_id]}_{thread_id}"
            
        url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "content": content,
            "allowed_mentions": {"parse": []},
        }
        try:
            with _httpx_client_factory() as client:
                resp = client.post(url, headers=headers, json=payload)
            if 200 <= resp.status_code < 300:
                log.info(
                    "%s ok thread_id=%s profile=%s content_len=%d status=%d guild_id=%s",
                    _DISCORD_DISPATCH_LOG_PREFIX, thread_id, profile,
                    len(content), resp.status_code, guild_id,
                )
            else:
                log.warning(
                    "%s http_error thread_id=%s profile=%s status=%d body_len=%d guild_id=%s",
                    _DISCORD_DISPATCH_LOG_PREFIX, thread_id, profile,
                    resp.status_code, len(resp.text or ""), guild_id,
                )
        except _httpx.HTTPError as e:
            log.warning(
                "%s network_error thread_id=%s profile=%s err=%s guild_id=%s",
                _DISCORD_DISPATCH_LOG_PREFIX, thread_id, profile,
                type(e).__name__, guild_id,
            )
        except Exception as e:
            log.exception(
                "%s unexpected_error thread_id=%s profile=%s err=%s guild_id=%s",
                _DISCORD_DISPATCH_LOG_PREFIX, thread_id, profile,
                type(e).__name__, guild_id,
            )

# ---------------------------------------------------------------------------
# Profile allowlist
# ---------------------------------------------------------------------------
def _known_profiles() -> set[str]:
    """Return the set of valid jarvis profile slugs.

    D-2026-06-09 (Phase 4, sub-task 4.0): single source of truth is
    `KNOWN_PROFILES` in `jarvis_company_os.registry` (derived from
    TEAM_MAP). Runtime supplements with `_profile_dirs()` from
    agent_growth so profiles that exist on disk but aren't in
    TEAM_MAP are still accepted — but TEAM_MAP is the floor: if a
    profile isn't in TEAM_MAP, it doesn't get to post to Discord.
    """
    slugs = set(_REGISTRY_PROFILES)
    try:
        from api.agent_growth import _profile_dirs as _ag_profile_dirs
        slugs.update(p.name for p in _ag_profile_dirs())
    except Exception:
        pass
    return slugs

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class PostMessageRequest(BaseModel):
    project: str = Field(..., min_length=1, max_length=64)
    profile: str = Field(..., min_length=1, max_length=64)
    content: str = Field(..., min_length=1, max_length=4000)
    guild_id: str = Field(None, min_length=1, max_length=64)  # Multi-guild (r20)

    @field_validator("project")
    @classmethod
    def _project_is_safe(cls, value: str) -> str:
        if not SAFE_PROJECT.match(value):
            raise ValueError("project must match [a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}")
        return value

class EnsureThreadRequest(BaseModel):
    project: str = Field(..., min_length=1, max_length=64)
    parent_channel_id: str = Field(..., min_length=1, max_length=64)
    guild_id: str = Field(None, min_length=1, max_length=64)  # Multi-guild (r20)

    @field_validator("project")
    @classmethod
    def _project_is_safe(cls, value: str) -> str:
        if not SAFE_PROJECT.match(value):
            raise ValueError("project must match [a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}")
        return value

# ---------------------------------------------------------------------------
# JSON state helpers
# ---------------------------------------------------------------------------
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# Discord dispatch (real REST call — Phase 6)
# ---------------------------------------------------------------------------
# Env-driven best-effort side channel. The dashboard JSON is the source
# of truth; this function is called AFTER `_mutate_state()` and never
# blocks the API response. All exceptions are swallowed and logged with
# ids/sizes only (no message content).
import httpx as _httpx  # local alias to keep the rest of the module's httpx-free

DISCORD_API_BASE = "https://discord.com/api/v10"
_DISCORD_TIMEOUT_S = 5.0
_DISCORD_DISPATCH_LOG_PREFIX = "discord-gateway.dispatch"

def _discord_bot_token() -> str:
    """Read JARVIS_DISCORD_BOT_TOKEN from env. Empty string = no token."""
    return os.environ.get("JARVIS_DISCORD_BOT_TOKEN", "").strip()

def _discord_httpx_client_factory():
    """Return a callable that produces a configured `httpx.Client`.

    Indirected so tests can swap in `httpx.MockTransport` without
    monkey-patching this module. The factory is called per request so
    connection pooling is opt-in (callers can wrap this in a cached
    client later if needed).
    """
    def _factory():
        return _httpx.Client(timeout=_DISCORD_TIMEOUT_S)
    return _factory

_httpx_client_factory = _discord_httpx_client_factory()

gateway = DiscordGateway()

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/messages")
def post_message(req: PostMessageRequest, _user: str = Depends(get_current_user)):
    """Record a message from a jarvis profile to the project's thread.

    Looks up (or auto-creates) the thread for the project slug. Returns
    the assigned thread_id and the recorded message_id. Rejects with 422
    if `profile` is not in the known-profile allowlist.

    D-2026-06-09 (Phase 5): requires auth (was unauthenticated in v1).
    Concurrent posts are serialized through `_mutate_state` so we
    cannot create duplicate threads or drop messages.
    """
    known = _known_profiles()
    if req.profile not in known:
        raise HTTPException(
            status_code=422,
            detail=f"unknown profile '{req.profile}'. "
                   f"Allowed: {sorted(known)}",
        )

    captured: dict = {}

    def _mutation(state: dict) -> None:
        threads = state["threads"]
        messages = state["messages"]

        thread = threads.get(req.project)
        if thread is None:
            thread_id = f"thr_{uuid.uuid4().hex[:12]}"
            thread = {
                "thread_id": thread_id,
                "parent_channel_id": "coding_plan_feedback",
                "created_at": _now(),
                "guild_id": req.guild_id,  # Multi-guild (r20)
            }
            threads[req.project] = thread
            captured["created"] = True
        else:
            thread_id = thread["thread_id"]
            captured["created"] = False
        captured["thread_id"] = thread_id

        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        messages.append({
            "message_id": message_id,
            "project": req.project,
            "profile": req.profile,
            "content": req.content,
            "posted_at": _now(),
            "thread_id": thread_id,
            "guild_id": req.guild_id,  # Multi-guild (r20)
        })
        captured["message_id"] = message_id

    gateway._mutate_state(_mutation)

    gateway._dispatch_to_discord(
        thread_id=captured["thread_id"],
        profile=req.profile,
        content=req.content,
        guild_id=req.guild_id,  # Multi-guild (r20)
    )

    log.info(
        "discord-gateway.post project=%s profile=%s thread_id=%s message_id=%s "
        "created_thread=%s content_len=%d guild_id=%s",
        req.project, req.profile, captured["thread_id"],
        captured["message_id"], captured["created"], len(req.content),
        req.guild_id,
    )

    return {
        "status": "ok",
        "thread_id": captured["thread_id"],
        "message_id": captured["message_id"],
        "created_thread": captured["created"],
        "writes_profile_configs": WRITES_PROFILE_CONFIGS,
    }

@router.get("/threads")
def list_threads(_user: str = Depends(get_current_user)):
    """Return the project → thread_id mapping. Auth required (Phase 5)."""
    state = gateway._read_state()
    return {
        "threads": state["threads"],
        "writes_profile_configs": WRITES_PROFILE_CONFIGS,
    }

@router.post("/threads/ensure")
def ensure_thread(req: EnsureThreadRequest, _user: str = Depends(get_current_user)):
    """Idempotently create a thread for a project. Auth required (Phase 5).

    Returns the existing thread if the project already has one, otherwise
    creates a new thread under the requested parent channel and returns
    it. The `created` flag tells the caller which case it was.

    Note: per the user-locked architecture (1 channel
    `#coding_plan_feedback` + per-project threads), the parent channel
    is implicitly fixed at the system level. If a caller supplies a
    `parent_channel_id` that differs from the existing one, we still
    return the existing thread (idempotency wins over caller intent) —
    a follow-up sync API can be added in Phase 4 if the parent ever
    needs to change.
    """
    captured: dict = {}

    def _mutation(state: dict) -> None:
        threads = state["threads"]
        existing = threads.get(req.project)
        if existing is not None:
            captured["created"] = False
            captured["thread_id"] = existing["thread_id"]
            captured["parent_channel_id"] = existing["parent_channel_id"]
            captured["guild_id"] = existing.get("guild_id")  # Multi-guild (r20)
            return
        thread_id = f"thr_{uuid.uuid4().hex[:12]}"
        threads[req.project] = {
            "thread_id": thread_id,
            "parent_channel_id": req.parent_channel_id,
            "created_at": _now(),
            "guild_id": req.guild_id,  # Multi-guild (r20)
        }
        captured["created"] = True
        captured["thread_id"] = thread_id
        captured["parent_channel_id"] = req.parent_channel_id
        captured["guild_id"] = req.guild_id

    gateway._mutate_state(_mutation)

    log.info(
        "discord-gateway.ensure project=%s thread_id=%s created=%s guild_id=%s",
        req.project, captured["thread_id"], captured["created"], captured.get("guild_id"),
    )

    return {
        "status": "ok",
        "project": req.project,
        "thread_id": captured["thread_id"],
        "parent_channel_id": captured["parent_channel_id"],
        "guild_id": captured.get("guild_id"),  # Multi-guild (r20)
        "created": captured["created"],
        "writes_profile_configs": WRITES_PROFILE_CONFIGS,
    }

@router.get("/messages")
def list_messages(
    project: str = Query(..., min_length=1, max_length=64),
    guild_id: str = Query(None, min_length=1, max_length=64),  # Multi-guild (r20)
    limit: int = Query(50, ge=1, le=500),
    _user: str = Depends(get_current_user),
):
    """Return recent messages for a project's thread, newest first. Auth required (Phase 5)."""
    if not SAFE_PROJECT.match(project):
        raise HTTPException(
            status_code=422,
            detail="project must match [a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}",
        )

    state = gateway._read_state()
    if project not in state["threads"]:
        return {
            "project": project,
            "messages": [],
            "writes_profile_configs": WRITES_PROFILE_CONFIGS,
        }

    filtered = [m for m in state["messages"] if m.get("project") == project]
    if guild_id:
        filtered = [m for m in filtered if m.get("guild_id") == guild_id]  # Multi-guild (r20)
    filtered.sort(key=lambda m: m.get("posted_at", ""), reverse=True)
    return {
        "project": project,
        "messages": filtered[:limit],
        "writes_profile_configs": WRITES_PROFILE_CONFIGS,
    }