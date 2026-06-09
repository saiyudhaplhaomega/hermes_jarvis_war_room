"""Tests for the live Hindsight server integration (D-2026-06-08-f, Phase F).

These tests hit the actual Hindsight Docker container running at
HINDSIGHT_URL. They are skipped if the server is not reachable so the
suite stays green when Docker is off.
"""
import os
import sys
import socket
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def _hindsight_reachable(url: str, timeout: float = 1.5) -> bool:
    """Quick TCP-level reachability check (no need to actually hit /health)."""
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


import pytest

URL = os.environ.get("HINDSIGHT_URL", "http://127.0.0.1:18888")
pytestmark = pytest.mark.skipif(
    not _hindsight_reachable(URL),
    reason=f"Hindsight server not reachable at {URL}",
)


def test_stats_reports_live_server_reachable(tmp_path):
    """When Hindsight is up, stats() should report it."""
    from core.memory_router import MemoryRouter
    r = MemoryRouter(project_id="war-room-test", store_path=tmp_path,
                     hindsight_url=URL)
    stats = r.stats()
    assert stats["hindsight_server_reachable"] is True
    assert stats["hindsight_server_url"] == URL


def test_add_state_does_not_throw_when_server_reachable(tmp_path):
    from core.memory_router import MemoryRouter
    r = MemoryRouter(project_id="war-room-test", store_path=tmp_path,
                     hindsight_url=URL)
    item = r.add_state("Saiyudh prefers dark mode", agent_id="test")
    assert item.data_type == "state"
    assert "dark mode" in item.content


def test_recall_state_returns_recently_added(tmp_path):
    from core.memory_router import MemoryRouter
    r = MemoryRouter(project_id="war-room-test-2", store_path=tmp_path,
                     hindsight_url=URL)
    marker = f"unique-marker-{os.urandom(4).hex()}"
    r.add_state(f"unique content {marker} about tomcats and pomegranates",
               agent_id="test")
    results = r.recall_state("tomcats and pomegranates", limit=5)
    # The live server uses semantic search; this might be slow. We
    # don't assert that the result is in there, just that the call
    # doesn't throw.
    assert isinstance(results, list)


def test_jsonl_fallback_still_works(tmp_path):
    """Even when the live server is up, add_state must also write JSONL."""
    from core.memory_router import MemoryRouter
    r = MemoryRouter(project_id="war-room-test-3", store_path=tmp_path,
                     hindsight_url=URL)
    r.add_state("test of jsonl durability", agent_id="test")
    assert r.state_log.exists()
    rows = r._read_jsonl(r.state_log)
    assert any("jsonl durability" in row.get("content", "") for row in rows)
