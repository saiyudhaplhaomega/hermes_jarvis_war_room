"""Tests for the Discord gateway v2 module (D-2026-06-09, Phase 3).

The gateway is the dashboard-side of the user's locked architecture:
  1 channel `#coding_plan_feedback` + per-project threads. All 14 jarvis
profiles can post to it. Messages route to a thread based on project slug.
A JSON file maps `project_slug -> thread_id` and the storage path is
env-overridable.

The Discord API call is a stub (Phase 4 wires discord.py). Tests never
reach out to Discord. The `writes_profile_configs: false` invariant is
preserved on every code path, including the JSON-file write handler.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def _load_app(monkeypatch, tmp_path):
    """Reload the FastAPI app with a temp gateway state file + temp profiles dir.

    Mirrors the canonical pattern at `tests/test_agent_growth_api.py:11-22`.
    We pop the server and the discord_gateway module from sys.modules so the
    env-var-bound storage paths are picked up on re-import. We also seed a
    synthetic `HERMES_PROFILES_DIR` containing the 14 user-locked jarvis
    profiles (with stub `config.yaml` files) so `_profile_dirs()` from
    `agent_growth.py` returns the right allowlist for this test in
    isolation.
    """
    monkeypatch.setenv("JARVIS_DASHBOARD_DEV_TOKEN", "test-token")
    monkeypatch.setenv("JARVIS_DASHBOARD_QUERY_TOKEN_FALLBACK", "1")
    monkeypatch.setenv(
        "JARVIS_DISCORD_GATEWAY_STATE", str(tmp_path / "discord_gateway.json")
    )

    # Seed HERMES_PROFILES_DIR with the 14 user-locked jarvis profiles.
    # This makes `_profile_dirs()` in `agent_growth.py` return exactly the
    # 14 names the gateway must accept — independent of which profiles
    # happen to be on the test host's live filesystem. The set matches
    # the actual PROFILE dir snapshot in
    # C:/Users/saiyu/AppData/Local/hermes/profiles/.
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    locked_profiles = [
        "jarvis-backend",
        "jarvis-council-departments",
        "jarvis-customer-success",
        "jarvis-data-ml",
        "jarvis-devops",
        "jarvis-finance",
        "jarvis-frontend",
        "jarvis-legal",
        "jarvis-marketing",
        "jarvis-mobile",
        "jarvis-researcher",
        "jarvis-sales",
        "jarvis-secretary",
        "jarvis-ui_ux",
    ]
    for slug in locked_profiles:
        (profiles_dir / slug).mkdir(parents=True, exist_ok=True)
        (profiles_dir / slug / "config.yaml").write_text(
            f"name: {slug}\nrole: stub\nmodel: codex\n"
        )
    monkeypatch.setenv("HERMES_PROFILES_DIR", str(profiles_dir))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))

    # Pop `core.config` and `server` so the env-var-bound paths
    # (`HERMES_HOME`, `HERMES_PROFILES_DIR`) are picked up on re-import.
    # `core.config.PROFILE` and `core.config.HERMES` are read once at
    # import time, so without popping, downstream test imports would
    # re-use stale paths.
    for name in list(sys.modules):
        if (
            name == "server"
            or name.startswith("api.discord_gateway")
            or name.startswith("api.agent_growth")
            or name == "core.config"
        ):
            sys.modules.pop(name, None)
    import server
    return server.app


def _token():
    return "test-token"


def test_post_message_creates_thread_for_new_project(monkeypatch, tmp_path):
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/messages?token={_token()}",
        json={
            "project": "jarvis-war-room",
            "profile": "jarvis-council-departments",
            "content": "first message ever for this project",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["thread_id"], "thread_id should be a non-empty id"
    assert payload["message_id"], "message_id should be a non-empty id"
    assert payload["writes_profile_configs"] is False

    # Persisted to the JSON store with the right shape.
    state_path = Path(
        __import__("os").environ["JARVIS_DISCORD_GATEWAY_STATE"]
    )
    state = json.loads(state_path.read_text())
    assert "jarvis-war-room" in state["threads"]
    assert state["threads"]["jarvis-war-room"]["thread_id"] == payload["thread_id"]
    assert len(state["messages"]) == 1
    assert state["messages"][0]["project"] == "jarvis-war-room"
    assert state["messages"][0]["profile"] == "jarvis-council-departments"
    assert (
        state["messages"][0]["content"]
        == "first message ever for this project"
    )


def test_post_message_routes_to_existing_thread(monkeypatch, tmp_path):
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    first = client.post(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/messages?token={_token()}",
        json={
            "project": "jarvis-war-room",
            "profile": "jarvis-council-departments",
            "content": "first",
        },
    )
    second = client.post(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/messages?token={_token()}",
        json={
            "project": "jarvis-war-room",
            "profile": "jarvis-frontend",
            "content": "second",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["thread_id"] == second.json()["thread_id"], (
        "second message to same project must reuse the existing thread"
    )
    assert first.json()["message_id"] != second.json()["message_id"]
    assert second.json()["writes_profile_configs"] is False

    # And only one thread entry exists.
    state = json.loads(
        Path(__import__("os").environ["JARVIS_DISCORD_GATEWAY_STATE"]).read_text()
    )
    assert len(state["threads"]) == 1
    assert len(state["messages"]) == 2


def test_post_message_rejects_unknown_profile(monkeypatch, tmp_path):
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/messages?token={_token()}",
        json={
            "project": "jarvis-war-room",
            "profile": "evil-bot",
            "content": "should be rejected",
        },
    )

    assert response.status_code == 422, response.text
    # Nothing should be persisted on a rejected request.
    state_path = Path(__import__("os").environ["JARVIS_DISCORD_GATEWAY_STATE"])
    if state_path.exists():
        state = json.loads(state_path.read_text())
        assert state.get("threads", {}) == {}
        assert state.get("messages", []) == []


def test_threads_ensure_is_idempotent(monkeypatch, tmp_path):
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    body = {"project": "jarvis-war-room", "parent_channel_id": "chan-abc-123"}
    first = client.post(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/threads/ensure?token={_token()}",
        json=body,
    )
    second = client.post(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/threads/ensure?token={_token()}",
        json=body,
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["thread_id"] == second_payload["thread_id"]
    assert first_payload["created"] is True
    assert second_payload["created"] is False
    assert first_payload["writes_profile_configs"] is False
    assert second_payload["writes_profile_configs"] is False

    # And only one thread entry.
    state = json.loads(
        Path(__import__("os").environ["JARVIS_DISCORD_GATEWAY_STATE"]).read_text()
    )
    assert len(state["threads"]) == 1


def test_list_threads_returns_mapping(monkeypatch, tmp_path):
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    # Seed two projects.
    for slug, parent in [("alpha", "chan-1"), ("beta", "chan-2")]:
        r = client.post(
            f"/api/plugins/jarvis-dashboard/v1/discord-gateway/threads/ensure?token={_token()}",
            json={"project": slug, "parent_channel_id": parent},
        )
        assert r.status_code == 200

    response = client.get(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/threads?token={_token()}"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["writes_profile_configs"] is False
    assert set(payload["threads"].keys()) == {"alpha", "beta"}
    assert payload["threads"]["alpha"]["parent_channel_id"] == "chan-1"
    assert payload["threads"]["beta"]["parent_channel_id"] == "chan-2"
    assert payload["threads"]["alpha"]["thread_id"]
    assert payload["threads"]["beta"]["thread_id"]


def test_get_messages_returns_recent_for_project(monkeypatch, tmp_path):
    """Bonus test: the messages listing endpoint filters by project."""
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    # Seed two projects, each with one message.
    for slug, profile in [("alpha", "jarvis-council-departments"), ("beta", "jarvis-frontend")]:
        r = client.post(
            f"/api/plugins/jarvis-dashboard/v1/discord-gateway/messages?token={_token()}",
            json={"project": slug, "profile": profile, "content": f"hi from {slug}"},
        )
        assert r.status_code == 200

    response = client.get(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/messages"
        f"?project=alpha&token={_token()}"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["writes_profile_configs"] is False
    assert payload["project"] == "alpha"
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["project"] == "alpha"
    assert payload["messages"][0]["profile"] == "jarvis-council-departments"


def test_all_responses_contain_writes_profile_configs_false(monkeypatch, tmp_path):
    """The `writes_profile_configs: false` invariant must be on every response.

    This is the load-bearing guard. If any future code path silently starts
    touching hermes profile configs, this test fails loud.
    """
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    # 1) POST messages (creates a thread + records a message).
    post_messages = client.post(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/messages?token={_token()}",
        json={
            "project": "invariant-project",
            "profile": "jarvis-council-departments",
            "content": "checking invariant",
        },
    )
    assert post_messages.status_code == 200
    assert post_messages.json()["writes_profile_configs"] is False

    # 2) POST threads/ensure (thread already exists now, should still flag false).
    ensure = client.post(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/threads/ensure?token={_token()}",
        json={"project": "invariant-project", "parent_channel_id": "chan-xyz"},
    )
    assert ensure.status_code == 200
    assert ensure.json()["writes_profile_configs"] is False

    # 3) GET threads.
    list_threads = client.get(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/threads?token={_token()}"
    )
    assert list_threads.status_code == 200
    assert list_threads.json()["writes_profile_configs"] is False

    # 4) GET messages.
    list_messages = client.get(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/messages"
        f"?project=invariant-project&token={_token()}"
    )
    assert list_messages.status_code == 200
    assert list_messages.json()["writes_profile_configs"] is False


# ---------------------------------------------------------------------------
# Phase 5: auth + concurrency hardening (codex major-task findings #2 and #4)
# ---------------------------------------------------------------------------
def test_all_endpoints_require_auth(monkeypatch, tmp_path):
    """D-2026-06-09 (Phase 5): discord gateway endpoints now require auth.

    Locks finding #2: every endpoint must depend on get_current_user.
    Missing/invalid token returns 401.
    """
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    # No token at all.
    r = client.post(
        "/api/plugins/jarvis-dashboard/v1/discord-gateway/messages",
        json={"project": "x", "profile": "jarvis-frontend", "content": "no auth"},
    )
    assert r.status_code == 401, r.text
    r = client.get("/api/plugins/jarvis-dashboard/v1/discord-gateway/threads")
    assert r.status_code == 401, r.text
    r = client.post(
        "/api/plugins/jarvis-dashboard/v1/discord-gateway/threads/ensure",
        json={"project": "x", "parent_channel_id": "c"},
    )
    assert r.status_code == 401, r.text
    r = client.get(
        "/api/plugins/jarvis-dashboard/v1/discord-gateway/messages?project=x"
    )
    assert r.status_code == 401, r.text


def test_concurrent_posts_preserve_message_count(monkeypatch, tmp_path):
    """D-2026-06-09 (Phase 5): concurrent posts must not drop messages
    or create duplicate thread IDs (codex major-task finding #4).

    Hammers the same project from 8 threads at once. After they all
    return, the persisted state must contain exactly 1 thread entry
    and exactly N=8 messages — no duplicates, no drops.
    """
    import threading as _threading
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    N = 8
    thread_ids: list = []
    lock = _threading.Lock()
    errors: list = []

    def post(i: int) -> None:
        try:
            r = client.post(
                f"/api/plugins/jarvis-dashboard/v1/discord-gateway/messages?token={_token()}",
                json={
                    "project": "concurrent-proj",
                    "profile": "jarvis-frontend",
                    "content": f"concurrent message {i}",
                },
            )
            assert r.status_code == 200, r.text
            with lock:
                thread_ids.append(r.json()["thread_id"])
        except Exception as e:
            with lock:
                errors.append(f"thread {i}: {type(e).__name__}: {e}")

    threads = [_threading.Thread(target=post, args=(i,)) for i in range(N)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    # All N responses used the SAME thread id.
    assert len(set(thread_ids)) == 1, thread_ids
    persisted_thread_id = thread_ids[0]

    state = json.loads(
        Path(__import__("os").environ["JARVIS_DISCORD_GATEWAY_STATE"]).read_text()
    )
    assert len(state["threads"]) == 1
    assert state["threads"]["concurrent-proj"]["thread_id"] == persisted_thread_id
    assert len(state["messages"]) == N


# ---------------------------------------------------------------------------
# Phase 6: real HTTP dispatcher (codex major-task finding #1)
# ---------------------------------------------------------------------------
def test_dispatch_makes_real_post_with_token_and_env(monkeypatch, tmp_path):
    """D-2026-06-09 (Phase 6): with a bot token, the dispatcher actually
    POSTs to the Discord REST API. We use httpx.MockTransport to
    intercept the call and assert the request shape (URL, headers,
    payload) without making a real network call.
    """
    import httpx
    from api import discord_gateway as dg

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(204, json={"id": "remote_msg_1"})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(dg, "_httpx_client_factory", lambda: httpx.Client(transport=transport))
    monkeypatch.setenv("JARVIS_DISCORD_BOT_TOKEN", "test-bot-token-xyz")

    app = _load_app(monkeypatch, tmp_path)
    # D-2026-06-09 (Phase 6): _load_app pops `api.discord_gateway`
    # from sys.modules and re-imports it via `import server`, so the
    # module object the test patched is a stale one. Re-apply the
    # factory override on the fresh module from sys.modules so the
    # route handler actually picks it up.
    import sys as _sys
    dg = _sys.modules["api.discord_gateway"]
    dg._httpx_client_factory = lambda: httpx.Client(transport=transport)
    client = TestClient(app)
    r = client.post(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/messages?token={_token()}",
        json={"project": "phase6-proj", "profile": "jarvis-frontend", "content": "phase6 hello"},
    )
    assert r.status_code == 200, r.text
    # The real Discord REST URL was called.
    assert captured["method"] == "POST"
    assert captured["url"] == "https://discord.com/api/v10/channels/" + r.json()["thread_id"] + "/messages"
    assert captured["headers"]["authorization"] == "Bot test-bot-token-xyz"
    assert captured["body"]["content"] == "phase6 hello"
    # No pings (best-effort side channel, no @everyone spam).
    assert captured["body"]["allowed_mentions"] == {"parse": []}


def test_dispatch_swallows_network_error(monkeypatch, tmp_path):
    """D-2026-06-09 (Phase 6): a Discord network failure MUST NOT
    cause the API to fail. The dashboard JSON is the source of truth;
    the side-channel failure is logged and dropped.
    """
    import httpx
    from api import discord_gateway as dg

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated network failure")

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(dg, "_httpx_client_factory", lambda: httpx.Client(transport=transport))
    monkeypatch.setenv("JARVIS_DISCORD_BOT_TOKEN", "test-bot-token-xyz")

    app = _load_app(monkeypatch, tmp_path)
    # See note in test_dispatch_makes_real_post_with_token_and_env:
    # re-apply the factory override on the freshly re-imported module.
    import sys as _sys
    dg = _sys.modules["api.discord_gateway"]
    dg._httpx_client_factory = lambda: httpx.Client(transport=transport)
    client = TestClient(app)
    r = client.post(
        f"/api/plugins/jarvis-dashboard/v1/discord-gateway/messages?token={_token()}",
        json={"project": "phase6-netfail", "profile": "jarvis-frontend", "content": "should still succeed"},
    )
    # API still returns 200 — the dispatcher failure is swallowed.
    assert r.status_code == 200, r.text
    # And the message is persisted in the JSON store.
    state = json.loads(
        Path(__import__("os").environ["JARVIS_DISCORD_GATEWAY_STATE"]).read_text()
    )
    assert "phase6-netfail" in state["threads"]
    assert any(m["content"] == "should still succeed" for m in state["messages"])
