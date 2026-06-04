import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def _load_app(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DASHBOARD_AGENT_SKILLS", str(tmp_path / "agent_skill_assignments.json"))
    monkeypatch.setenv("JARVIS_DASHBOARD_AGENT_PROPOSALS", str(tmp_path / "agent_proposals.json"))
    monkeypatch.setenv("JARVIS_DASHBOARD_REMOVED_AGENTS", str(tmp_path / "removed_agents.json"))
    monkeypatch.setenv("JARVIS_DASHBOARD_ROLE_MAPPINGS", str(tmp_path / "role_mappings.json"))
    monkeypatch.setenv("JARVIS_DASHBOARD_DEV_TOKEN", "test-token")
    monkeypatch.setenv("JARVIS_DASHBOARD_QUERY_TOKEN_FALLBACK", "1")
    for name in list(sys.modules):
        if name == "server" or name.startswith("api.agent_growth") or name.startswith("api.roles"):
            sys.modules.pop(name, None)
    import server
    return server.app


def test_skills_endpoint_returns_inventory_without_profile_writes(monkeypatch, tmp_path):
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/api/plugins/jarvis-dashboard/v1/skills?token=test-token")

    assert response.status_code == 200
    payload = response.json()
    assert payload["writes_profile_configs"] is False
    assert "skills" in payload
    assert isinstance(payload["skills"], list)
    if payload["skills"]:
        assert {"name", "description", "category", "source"} <= set(payload["skills"][0])


def test_agent_skill_assignments_are_overlay_only(monkeypatch, tmp_path):
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    skills = client.get("/api/plugins/jarvis-dashboard/v1/skills?token=test-token").json()["skills"]
    skill_name = skills[0]["name"] if skills else "jarvis-war-room-dashboard"
    profile_config = Path.home() / ".hermes/profiles/jarvis/config.yaml"
    before = profile_config.stat().st_mtime if profile_config.exists() else None

    response = client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/skills?token=test-token",
        json={"assignments": [{"agent": "jarvis", "skills": [skill_name], "notes": "test overlay"}]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["writes_profile_configs"] is False
    assert payload["assignments"][0]["agent"] == "jarvis"
    if before is not None:
        assert profile_config.stat().st_mtime == before


def test_agent_proposal_does_not_create_profile_directory(monkeypatch, tmp_path):
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    models = client.get("/api/plugins/jarvis-dashboard/v1/models?token=test-token").json()["models"]
    model = models[0] if models else {"provider": "ollama-cloud", "model": "kimi-k2.6"}
    target = Path.home() / ".hermes/profiles/jarvis-growth-test"
    assert not target.exists()

    response = client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/propose?token=test-token",
        json={
            "agent_name": "jarvis-growth-test",
            "description": "test proposal only",
            "provider": model["provider"],
            "model": model["model"],
            "clone_from": "jarvis",
            "skills": [],
            "notes": "proposal smoke test",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["writes_profile_configs"] is False
    assert payload["request"]["agent_name"] == "jarvis-growth-test"
    assert not target.exists()


def test_agent_growth_rejects_path_like_names(monkeypatch, tmp_path):
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/propose?token=test-token",
        json={
            "agent_name": "../bad",
            "description": "bad",
            "provider": "ollama-cloud",
            "model": "kimi-k2.6",
            "clone_from": "jarvis",
            "skills": [],
            "notes": "bad",
        },
    )

    assert response.status_code == 422


def test_remove_agent_creates_seven_day_backup_without_profile_delete(monkeypatch, tmp_path):
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    target = Path.home() / ".hermes/profiles/jarvis-growth-remove-test"
    assert not target.exists()

    proposal = client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/propose?token=test-token",
        json={
            "agent_name": "jarvis-growth-remove-test",
            "description": "remove test",
            "provider": "ollama-cloud",
            "model": "kimi-k2.6",
            "clone_from": "jarvis",
            "skills": [],
            "notes": "remove smoke",
        },
    )
    assert proposal.status_code == 200

    response = client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/remove?token=test-token",
        json={"agent_name": "jarvis-growth-remove-test", "reason": "user cleanup"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["writes_profile_configs"] is False
    removed = payload["removed_agent"]
    assert removed["agent_name"] == "jarvis-growth-remove-test"
    assert removed["status"] == "removed"
    assert removed["retention_days"] == 7
    assert removed["backup"]["proposal"]["request"]["agent_name"] == "jarvis-growth-remove-test"
    assert not target.exists()

    proposals = client.get("/api/plugins/jarvis-dashboard/v1/agents/proposals?token=test-token").json()["proposals"]
    assert all(item["request"]["agent_name"] != "jarvis-growth-remove-test" for item in proposals)


def test_restore_removed_agent_restores_proposal_and_skill_overlay(monkeypatch, tmp_path):
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    skill_name = client.get("/api/plugins/jarvis-dashboard/v1/skills?token=test-token").json()["skills"][0]["name"]
    client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/propose?token=test-token",
        json={
            "agent_name": "jarvis-growth-restore-test",
            "description": "restore test",
            "provider": "ollama-cloud",
            "model": "kimi-k2.6",
            "clone_from": "jarvis",
            "skills": [skill_name],
            "notes": "restore smoke",
        },
    )
    client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/skills?token=test-token",
        json={"assignments": [{"agent": "jarvis-growth-restore-test", "skills": [skill_name], "notes": "restore me"}]},
    )
    removed = client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/remove?token=test-token",
        json={"agent_name": "jarvis-growth-restore-test", "reason": "restore check"},
    ).json()["removed_agent"]

    response = client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/restore?token=test-token",
        json={"removed_id": removed["removed_id"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["writes_profile_configs"] is False
    assert payload["restored_agent"] == "jarvis-growth-restore-test"
    proposals = client.get("/api/plugins/jarvis-dashboard/v1/agents/proposals?token=test-token").json()["proposals"]
    assert any(item["request"]["agent_name"] == "jarvis-growth-restore-test" for item in proposals)
    assignments = client.get("/api/plugins/jarvis-dashboard/v1/agents/skills?token=test-token").json()["assignments"]
    restored_assignment = next(item for item in assignments if item["agent"] == "jarvis-growth-restore-test")
    assert restored_assignment["skills"] == [skill_name]
    removed_payload = client.get("/api/plugins/jarvis-dashboard/v1/agents/removed?token=test-token").json()
    restored = next(item for item in removed_payload["removed_agents"] if item["removed_id"] == removed["removed_id"])
    assert restored["status"] == "restored"


def test_permanent_delete_requires_confirm_text(monkeypatch, tmp_path):
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/propose?token=test-token",
        json={
            "agent_name": "jarvis-growth-delete-test",
            "description": "delete test",
            "provider": "ollama-cloud",
            "model": "kimi-k2.6",
            "clone_from": "jarvis",
            "skills": [],
            "notes": "delete smoke",
        },
    )
    removed = client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/remove?token=test-token",
        json={"agent_name": "jarvis-growth-delete-test", "reason": "delete check"},
    ).json()["removed_agent"]

    rejected = client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/permanent-delete?token=test-token",
        json={"removed_id": removed["removed_id"], "confirm_text": "nope"},
    )
    assert rejected.status_code == 422

    accepted = client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/permanent-delete?token=test-token",
        json={"removed_id": removed["removed_id"], "confirm_text": "DELETE jarvis-growth-delete-test"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["writes_profile_configs"] is False
