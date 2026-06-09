"""WebSocket connection manager.
Broadcasts aggregated snapshot updates to all connected clients.
Supports channel-based subscriptions.

D-2026-06-08-e (Phase E): upgraded to snapshot+delta protocol with
versioning, heartbeat, and resync (per Loop 5 R7).
"""
import json, asyncio, time
from fastapi import WebSocket
from typing import List, Set, Dict

# Global shared cache populated by data_aggregator._write_cache
LIVE_CACHE = {}
LIVE_CACHE_META = {"ts": ""}

# Protocol channels a client can subscribe to.
PROTOCOL_CHANNELS = {
    "agents",   # agent state changes
    "memory",   # memory bank updates
    "audit",    # audit log entries
    "topology", # company topology changes
    "council",  # council vote results
    "army",     # army run lifecycle
    "all",      # everything (default)
}


# ─────────────────────────────────────────────
# Message helpers (D-2026-06-08-e)
# ─────────────────────────────────────────────

def snapshot_message(payload: dict, version: int = 1) -> dict:
    """Initial snapshot sent on connect. Version is the high-water mark."""
    return {"type": "snapshot", "version": version, "payload": payload}


def make_delta(version: int, base_version: int, channel: str, payload: dict) -> dict:
    """A delta updates a subset. base_version lets the client detect gaps."""
    return {
        "type": "delta",
        "version": version,
        "base_version": base_version,
        "channel": channel,
        "payload": payload,
    }


def heartbeat_message() -> dict:
    """Server heartbeat so clients know the connection is alive."""
    return {"type": "heartbeat", "ts": time.time()}


def resync_request() -> dict:
    """Client → server: I lost sync, send me a fresh snapshot."""
    return {"type": "resync"}


# ─────────────────────────────────────────────
# Connection manager
# ─────────────────────────────────────────────

class ConnectionManager:
    """Manages WebSocket connections with per-channel subscriptions.

    Per Loop 5 R7: snapshot+delta with topic subscriptions. Full event
    stream is admin-only (use channel='all' with admin auth in a future
    revision).
    """

    def __init__(self):
        self.connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, Set[str]] = {}
        # Monotonic version counter; bump on every delta
        self.version: int = 0

    def bump_version(self) -> int:
        """Atomically increment the version counter. Returns the new value."""
        self.version += 1
        return self.version

    async def connect(self, websocket: WebSocket):
        # Auth BEFORE accept — reject invalid tokens at the WebSocket policy layer.
        try:
            from auth.dependencies import SESSION_COOKIE_NAME, get_current_user_ws
            get_current_user_ws(
                cookie_token=websocket.cookies.get(SESSION_COOKIE_NAME),
                authorization=websocket.headers.get("Authorization"),
                query_token=websocket.query_params.get("token"),
            )
        except Exception:
            await websocket.close(code=4001, reason="auth required")
            return False
        await websocket.accept()
        self.connections.append(websocket)
        # Default subscription: 'all' (so a client that just connects gets
        # everything). They can narrow it via subscribe() after the snapshot.
        self.subscriptions[websocket] = {"all"}
        # Push current snapshot immediately so client has data on connect
        from core.websocket import LIVE_CACHE
        try:
            self.bump_version()
            await self.send(websocket, snapshot_message(dict(LIVE_CACHE), version=self.version))
        except Exception:
            pass
        return True

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)
        self.subscriptions.pop(websocket, None)

    def subscribe(self, websocket: WebSocket, channels: List[str]):
        """Set channels this connection wants to receive. Replaces previous."""
        valid = set(channels) & PROTOCOL_CHANNELS
        # Always keep "all" so the client gets the snapshot on reconnect;
        # callers can opt out by passing an explicit non-empty list.
        if "all" not in valid and channels:
            # Caller wants specific channels, not 'all'
            self.subscriptions[websocket] = valid
        else:
            self.subscriptions[websocket] = valid

    def unsubscribe(self, websocket: WebSocket, channel: str):
        """Remove a single channel from this connection's subscriptions."""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].discard(channel)

    async def broadcast(self, payload: dict, channel: str = "all"):
        """Send a delta to all connections subscribed to channel."""
        dead = []
        new_version = self.bump_version()
        msg = json.dumps(
            make_delta(new_version, new_version - 1, channel, payload),
            default=str,
        )
        for ws in self.connections:
            subs = self.subscriptions.get(ws, set())
            if channel == "all" or channel in subs:
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def send(self, websocket: WebSocket, payload: dict):
        """Send a single message to one connection."""
        try:
            await websocket.send_text(json.dumps(payload, default=str))
        except Exception:
            self.disconnect(websocket)

# Singleton used by server + aggregator
manager = ConnectionManager()
