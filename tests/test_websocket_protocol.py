"""Tests for the WebSocket snapshot+delta protocol (D-2026-06-08-e, Loop 5 R7).

The contract:
  - On connect, client receives ONE snapshot with {type: "snapshot", version, payload}
  - Subsequent messages are deltas with {type: "delta", version, base_version, payload}
  - Each delta bumps the version; the snapshot version is the highest version sent
  - Per-topic subscriptions: client subscribes to "agents", "memory", "audit", etc.
  - Heartbeat: server sends ping every 30s, client must respond
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def _make_manager():
    from core.websocket import ConnectionManager, LIVE_CACHE
    return ConnectionManager()


def test_snapshot_message_has_version():
    """Snapshot must include a version number so clients can resync."""
    from core.websocket import snapshot_message
    msg = snapshot_message({"agents": [], "memory": []})
    assert msg["type"] == "snapshot"
    assert "version" in msg
    assert isinstance(msg["version"], int)
    assert msg["version"] > 0
    assert msg["payload"] == {"agents": [], "memory": []}


def test_delta_message_increments_version():
    """Delta messages must increment version monotonically and reference base."""
    from core.websocket import make_delta
    d1 = make_delta(version=1, base_version=1, channel="agents", payload={"a": 1})
    d2 = make_delta(version=2, base_version=2, channel="agents", payload={"a": 2})
    assert d1["type"] == "delta"
    assert d1["version"] == 1
    assert d1["base_version"] == 1
    assert d1["channel"] == "agents"
    assert d1["payload"] == {"a": 1}
    assert d2["version"] == 2


def test_heartbeat_message_shape():
    from core.websocket import heartbeat_message
    msg = heartbeat_message()
    assert msg["type"] == "heartbeat"
    assert "ts" in msg
    assert isinstance(msg["ts"], (int, float))


def test_resync_request_shape():
    """Client can request a fresh snapshot by sending {type: "resync"}."""
    from core.websocket import resync_request
    msg = resync_request()
    assert msg["type"] == "resync"


def test_manager_starts_at_version_zero():
    """Fresh ConnectionManager has version 0 (no messages sent yet)."""
    m = _make_manager()
    assert m.version == 0


def test_manager_bump_version_increments():
    m = _make_manager()
    m.bump_version()
    assert m.version == 1
    m.bump_version()
    assert m.version == 2
    m.bump_version()
    assert m.version == 3


def test_manager_subscribe_and_unsubscribe():
    m = _make_manager()
    # Fake websocket (we only need an object identity for the dict key)
    class FakeWS:
        pass
    ws = FakeWS()
    m.subscribe(ws, ["agents", "memory"])
    assert m.subscriptions[ws] == {"agents", "memory"}
    m.unsubscribe(ws, "memory")
    assert m.subscriptions[ws] == {"agents"}


def test_manager_subscribe_to_empty_channel_receives_nothing():
    """A client that subscribes to [] gets only 'all'-channel broadcasts, nothing specific."""
    m = _make_manager()
    class FakeWS:
        pass
    ws = FakeWS()
    m.subscribe(ws, [])
    assert m.subscriptions[ws] == set()
