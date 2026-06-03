"""WebSocket connection manager.
Broadcasts aggregated snapshot updates to all connected clients.
Supports channel-based subscriptions.
"""
import json, asyncio
from fastapi import WebSocket
from typing import List, Set, Dict

# Global shared cache populated by data_aggregator._write_cache
LIVE_CACHE = {}
LIVE_CACHE_META = {"ts": ""}

class ConnectionManager:
    """Manages WebSocket connections with per-channel subscriptions."""

    def __init__(self):
        self.connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket):
        # Auth BEFORE accept — reject invalid tokens at HTTP layer
        token = websocket.query_params.get("token", "")
        try:
            from auth.dependencies import get_current_user_ws
            user = get_current_user_ws(token)
        except Exception:
            await websocket.close(code=4001, reason="auth required")
            return
        await websocket.accept()
        self.connections.append(websocket)
        self.subscriptions[websocket] = set()
        # Push current cache immediately so client has data on connect
        from core.websocket import LIVE_CACHE
        try:
            await self.send(websocket, {"type": "snapshot", "payload": dict(LIVE_CACHE)})
        except Exception:
            pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)
        self.subscriptions.pop(websocket, None)

    def subscribe(self, websocket: WebSocket, channels: List[str]):
        """Set channels this connection wants to receive."""
        self.subscriptions[websocket] = set(channels)

    async def broadcast(self, payload: dict, channel: str = "all"):
        """Send message to all connections subscribed to channel."""
        dead = []
        msg = json.dumps(payload, default=str)
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
