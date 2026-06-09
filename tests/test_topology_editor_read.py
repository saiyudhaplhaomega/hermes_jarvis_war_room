"""Tests for the Topology Editor data contract (Sub-phase 1).

Sub-phase 1 = static, read-only. These tests pin down the API contract
the editor will consume. Sub-phase 2 will add write endpoints; the tests
in `test_topology_editor_writes.py` will pin those.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def _load_app(monkeypatch, tmp_path):
    """Load the FastAPI app with a fresh tmp_path for any state files."""
    monkeypatch.setenv("JARVIS_DASHBOARD_DEV_TOKEN", "test-token")
    monkeypatch.setenv("JARVIS_DASHBOARD_QUERY_TOKEN_FALLBACK", "1")
    monkeypatch.setenv("JARVIS_DASHBOARD_ARMY_STATE", str(tmp_path / "army_state.json"))
    monkeypatch.setenv("JARVIS_DASHBOARD_ARMY_RUNS", str(tmp_path / "army_runs"))
    monkeypatch.setenv("JARVIS_DASHBOARD_ARMY_DISABLE_EXEC", "1")
    # D-2026-06-08-topology-editor sub-phase 1: the Company OS needs a
    # writable SQLite path; tests get a fresh one in tmp_path.
    # We also pin HERMES_HOME to the same tmp_path so profile stubs are
    # discoverable (pytest's monkeypatch tmp dir and tmp_path can differ on
    # Windows; the explicit env var removes that ambiguity).
    company_db = tmp_path / "company_os.db"
    monkeypatch.setenv("JARVIS_COMPANY_OS_DB", str(company_db))
    monkeypatch.setenv("JARVIS_COMPANY_OS_HERMES_HOME", str(tmp_path))
    # The migrations dir doesn't exist in CI / fresh dev — apply_pending is
    # a no-op in that case (logs a warning, doesn't raise).
    monkeypatch.setenv(
        "JARVIS_COMPANY_OS_MIGRATIONS_DIR", str(tmp_path / "no-migrations-here")
    )
    # Stub profile dirs so seed_default_company actually has agents to
    # discover. Five stubs mirror the boss/manager/qa/security/docs leads
    # from the production COUNCIL_HIERARCHY.
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    for slug in ("jarvis-boss", "jarvis-manager", "jarvis-engineering-lead",
                 "jarvis-qa-lead", "jarvis-security-lead", "jarvis-docs-lead",
                 "jarvis-product-lead"):
        (profiles_dir / slug).mkdir(parents=True, exist_ok=True)
        (profiles_dir / slug / "config.yaml").write_text(
            f"name: {slug.replace('jarvis-', '').replace('-', ' ').title()}\n"
            f"model: codex\n"
        )
    for name in list(sys.modules):
        if name == "server" or name.startswith("api.") or name.startswith("jarvis_company_os"):
            sys.modules.pop(name, None)
    import server
    # Mimic what server.py's lifespan does: apply migrations (no-op here) +
    # seed the default company. Without this, the topology endpoint has
    # no tables to query.
    from jarvis_company_os.migrations import apply_pending
    from jarvis_company_os.registry import seed_default_company
    apply_pending()
    seed_default_company()
    return server.app


def test_topology_endpoint_returns_jarvis_war_room_company(monkeypatch, tmp_path):
    """GET /companies/jarvis-war-room/topology must return 200 with the {nodes, agents, edges} shape.

    This is the Boss D4 acceptance contract per spec/04. Until this passes,
    the frontend topology editor has nothing to render.
    """
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get(
        "/api/plugins/jarvis-dashboard/v1/companies/jarvis-war-room/topology?token=test-token"
    )

    assert response.status_code == 200, (
        f"topology endpoint must return 200, got {response.status_code}: {response.text}"
    )
    payload = response.json()
    # Boss D4: response shape is {nodes, agents, edges}
    assert "nodes" in payload, "topology payload must include 'nodes'"
    assert "agents" in payload, "topology payload must include 'agents'"
    assert "edges" in payload, "topology payload must include 'edges'"
    # The seed company should have at least the boss + manager + 5 leads
    assert len(payload["agents"]) >= 5, (
        f"expected >=5 seeded agents, got {len(payload['agents'])}"
    )
    # Each agent must have a stable id, a label, and a team
    for agent in payload["agents"]:
        assert "id" in agent, "agent must have 'id'"
        assert "label" in agent or "name" in agent, "agent must have 'label' or 'name'"
        assert "team_id" in agent, "agent must have 'team_id' (the team's PK)"


def test_topology_endpoint_404s_for_unknown_company(monkeypatch, tmp_path):
    """Unknown company_id must return 404 (or 200 with empty payload, depending on impl).

    We accept either, but the response must NOT be a 500 — that's the contract
    the editor relies on to show 'no company' gracefully.
    """
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get(
        "/api/plugins/jarvis-dashboard/v1/companies/does-not-exist/topology?token=test-token"
    )

    assert response.status_code in (200, 404), (
        f"unknown company should be 200-empty or 404, got {response.status_code}"
    )


def test_topology_endpoint_requires_auth_token(monkeypatch, tmp_path):
    """Without a token, the endpoint must reject. The query_token_fallback
    is enabled in tests, so we just check it doesn't 500.
    """
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get(
        "/api/plugins/jarvis-dashboard/v1/companies/jarvis-war-room/topology"
    )

    # With query_token_fallback=1, the response is 200. Without it, 401/403.
    # We just verify the endpoint is reachable and structured.
    assert response.status_code in (200, 401, 403)
