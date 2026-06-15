import importlib
import sys
from pathlib import Path

import pytest
from fastapi import WebSocketException, status
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))


def _reload_backend(monkeypatch, tmp_path, *, query_fallback="0", state_overrides=None):
    monkeypatch.setenv("JARVIS_DASHBOARD_DEV_TOKEN", "test-token")
    monkeypatch.setenv("JARVIS_DASHBOARD_QUERY_TOKEN_FALLBACK", query_fallback)
    state_paths = {
        "JARVIS_DASHBOARD_ROLE_MAPPINGS": "roles.json",
        "JARVIS_DISCORD_GATEWAY_STATE": "discord_gateway.json",
        "JARVIS_DASHBOARD_COUNCIL_DECISIONS": "council_decisions.json",
        "JARVIS_DASHBOARD_AGENT_SKILLS": "agent_skill_assignments.json",
        "JARVIS_DASHBOARD_SKILL_CATALOG": "skill_catalog.json",
        "JARVIS_DASHBOARD_AGENT_PROPOSALS": "agent_proposals.json",
        "JARVIS_DASHBOARD_REMOVED_AGENTS": "removed_agents.json",
    }
    for key, filename in state_paths.items():
        monkeypatch.setenv(key, str(tmp_path / filename))
    for key, value in (state_overrides or {}).items():
        monkeypatch.setenv(key, str(value))
    monkeypatch.setenv("JARVIS_DASHBOARD_ARMY_STATE", str(tmp_path / "army_state.json"))
    monkeypatch.setenv("JARVIS_DASHBOARD_ARMY_RUNS", str(tmp_path / "army_runs"))
    monkeypatch.setenv("JARVIS_DASHBOARD_ARMY_DISABLE_EXEC", "1")
    for name in list(sys.modules):
        if (
            name == "server"
            or name.startswith("auth.")
            or name == "core.config"
            or name.startswith("core.websocket")
            or name in {"api.discord_gateway", "api.council", "api.agent_growth", "api.roles"}
        ):
            sys.modules.pop(name, None)
    import server
    return server


def test_rest_auth_accepts_bearer_header_and_rejects_query_by_default(monkeypatch, tmp_path):
    _reload_backend(monkeypatch, tmp_path, query_fallback="0")
    from auth.dependencies import get_current_user
    from fastapi import FastAPI, Depends

    app = FastAPI()

    @app.get("/protected")
    def protected(user: str = Depends(get_current_user)):
        return {"user": user}

    client = TestClient(app)

    assert client.get("/protected", headers={"Authorization": "Bearer test-token"}).json() == {"user": "saiyudh"}
    assert client.get("/protected?token=test-token").status_code == 401
    assert client.get("/protected").status_code == 401


def test_query_token_fallback_requires_explicit_env_flag(monkeypatch, tmp_path):
    _reload_backend(monkeypatch, tmp_path, query_fallback="1")
    from auth.dependencies import get_current_user
    from fastapi import FastAPI, Depends

    app = FastAPI()

    @app.get("/protected")
    def protected(user: str = Depends(get_current_user)):
        return {"user": user}

    client = TestClient(app)
    assert client.get("/protected?token=test-token").status_code == 200


def test_auth_session_sets_httponly_cookie_and_ready_endpoint_exists(monkeypatch, tmp_path):
    server = _reload_backend(monkeypatch, tmp_path, query_fallback="0")
    client = TestClient(server.app)

    session = client.post(
        "/api/plugins/jarvis-dashboard/v1/auth/session",
        headers={"Authorization": "Bearer test-token"},
    )

    assert session.status_code == 200
    assert session.json()["user"] == "saiyudh"
    cookie = session.headers.get("set-cookie", "")
    assert "jarvis-dashboard-token=" in cookie
    assert "HttpOnly" in cookie
    assert "samesite=lax" in cookie.lower()
    assert "test-token" not in session.text

    ready = client.get("/api/plugins/jarvis-dashboard/v1/ready", headers={"Authorization": "Bearer test-token"})
    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "ready"
    assert set(body["state_paths"]) == {
        "gateway",
        "council",
        "agent_growth_assignments",
        "catalog",
        "proposals",
        "removed_agents",
        "role_mappings",
    }
    assert all(item["writable"] is True for item in body["state_paths"].values())
    assert "test-token" not in ready.text


def test_ready_reports_unwritable_json_state_path(monkeypatch, tmp_path):
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not a directory")
    server = _reload_backend(
        monkeypatch,
        tmp_path,
        query_fallback="0",
        state_overrides={"JARVIS_DISCORD_GATEWAY_STATE": blocked_parent / "discord_gateway.json"},
    )
    client = TestClient(server.app)

    ready = client.get("/api/plugins/jarvis-dashboard/v1/ready", headers={"Authorization": "Bearer test-token"})

    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "degraded"
    assert body["state_paths"]["gateway"]["writable"] is False
    assert "path" not in body["state_paths"]["gateway"]
    assert "test-token" not in ready.text


def test_cors_rejects_public_ip_origin_by_default_but_allows_local(monkeypatch, tmp_path):
    server = _reload_backend(monkeypatch, tmp_path, query_fallback="0")
    client = TestClient(server.app)

    allowed = client.options(
        "/api/plugins/jarvis-dashboard/v1/ready",
        headers={
            "Origin": "http://127.0.0.1:8503",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    denied = client.options(
        "/api/plugins/jarvis-dashboard/v1/ready",
        headers={
            "Origin": "http://43.131.26.109:8503",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers.get("access-control-allow-origin") == "http://127.0.0.1:8503"
    assert denied.headers.get("access-control-allow-origin") is None


def test_ws_auth_accepts_cookie_or_bearer_and_rejects_query_by_default(monkeypatch, tmp_path):
    _reload_backend(monkeypatch, tmp_path, query_fallback="0")
    from auth.dependencies import get_current_user_ws

    assert get_current_user_ws(cookie_token="test-token") == "saiyudh"
    assert get_current_user_ws(authorization="Bearer test-token") == "saiyudh"
    with pytest.raises(WebSocketException) as exc:
        get_current_user_ws(query_token="test-token")
    assert exc.value.code == status.WS_1008_POLICY_VIOLATION


def test_spa_server_csp_and_runtime_config_do_not_emit_query_token(monkeypatch):
    monkeypatch.setenv("JARVIS_DASHBOARD_DEV_TOKEN", "test-token")
    import spa_server
    importlib.reload(spa_server)

    csp = spa_server._content_security_policy()
    assert "ws://*" not in csp
    assert "wss://*" not in csp
    assert "connect-src 'self'" in csp
    assert "?token=" not in spa_server.RUNTIME_CONFIG


def test_frontend_source_does_not_construct_token_query_urls():
    files = [
        ROOT / "frontend-react" / "src" / "api" / "client.ts",
        ROOT / "frontend-react" / "src" / "contexts" / "ConnectionContext.tsx",
    ]
    combined = "\n".join(path.read_text() for path in files)
    assert "?token=" not in combined
    assert "Authorization" in combined


def test_project_local_logrotate_candidate_exists_and_targets_audit_log():
    candidate = ROOT / "ops" / "logrotate" / "jarvis-dashboard-audit"
    text = candidate.read_text()
    assert "/home/ubuntu/.hermes/profiles/jarvis/plugins/jarvis-dashboard" in text
    assert "copytruncate" in text
    assert "/etc/logrotate.d" not in text


def test_all_backend_service_artifacts_are_localhost_bound_and_disable_access_logs():
    for rel in ["jarvis-dashboard-backend.service", "systemd/jarvis-dashboard.service"]:
        text = (ROOT / rel).read_text()
        assert "--host 127.0.0.1" in text
        assert "--host 0.0.0.0" not in text
        assert "--no-access-log" in text


def test_all_static_service_artifacts_serve_react_dist_and_bind_localhost():
    for rel in ["jarvis-dashboard-static.service", "systemd/jarvis-dashboard-static.service"]:
        text = (ROOT / rel).read_text()
        assert "frontend-react/dist" in text
        assert "frontend/public" not in text
        assert " 127.0.0.1" in text


def test_sse_session_sets_httponly_cookie_and_never_returns_token(monkeypatch, tmp_path):
    server = _reload_backend(monkeypatch, tmp_path, query_fallback="0")
    client = TestClient(server.app)

    response = client.post(
        "/api/plugins/jarvis-dashboard/v1/sse-session",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 204
    cookie = response.headers.get("set-cookie", "")
    assert "jarvis-dashboard-token=" in cookie
    assert "HttpOnly" in cookie
    assert "samesite=lax" in cookie.lower()
    assert "test-token" not in response.text


def test_sse_events_rejects_query_token_even_when_query_fallback_enabled(monkeypatch, tmp_path, caplog):
    server = _reload_backend(monkeypatch, tmp_path, query_fallback="1")
    client = TestClient(server.app)

    with caplog.at_level("WARNING"):
        response = client.get("/api/plugins/jarvis-dashboard/v1/events?token=test-token")

    assert response.status_code == 401
    assert "test-token" not in response.text
    combined_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "sse_token_url_rejected" in combined_logs
    assert "test-token" not in combined_logs


def test_sse_events_accepts_session_cookie_and_streams_initial_event(monkeypatch, tmp_path):
    server = _reload_backend(monkeypatch, tmp_path, query_fallback="0")
    client = TestClient(server.app)
    session = client.post(
        "/api/plugins/jarvis-dashboard/v1/sse-session",
        headers={"Authorization": "Bearer test-token"},
    )
    assert session.status_code == 204

    with client.stream("GET", "/api/plugins/jarvis-dashboard/v1/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        first_chunk = next(response.iter_text())
        assert "event: ready" in first_chunk
        assert "test-token" not in first_chunk


def test_route_policy_exact_allowlist_matches_registered_routes(monkeypatch, tmp_path):
    server = _reload_backend(monkeypatch, tmp_path, query_fallback="0")
    from core.route_policy import EXPECTED_ROUTE_POLICY

    actual = {
        (tuple(sorted(route.methods or [])), route.path)
        for route in server.app.routes
        if hasattr(route, "methods")
    }
    expected = {
        (tuple(methods), path)
        for methods, path in EXPECTED_ROUTE_POLICY
    }
    assert actual == expected


def test_frontend_source_uses_eventsource_credentials_without_token_url():
    files = [
        ROOT / "frontend-react" / "src" / "api" / "client.ts",
        ROOT / "frontend-react" / "src" / "contexts" / "ConnectionContext.tsx",
    ]
    combined = "\n".join(path.read_text() for path in files)
    assert "new EventSource" in combined
    assert "withCredentials: true" in combined
    assert "?token=" not in combined
    assert "/events?" not in combined

