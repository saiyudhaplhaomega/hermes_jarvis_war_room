import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def _load_app(monkeypatch, tmp_path):
    data_file = tmp_path / "role_mappings.json"
    monkeypatch.setenv("JARVIS_DASHBOARD_ROLE_MAPPINGS", str(data_file))
    monkeypatch.setenv("JARVIS_DASHBOARD_DEV_TOKEN", "test-token")
    monkeypatch.setenv("JARVIS_DASHBOARD_QUERY_TOKEN_FALLBACK", "1")
    for name in list(sys.modules):
        if name == "server" or name.startswith("api.roles"):
            sys.modules.pop(name, None)
    import server
    return server.app, data_file


def test_roles_default_is_dashboard_local_and_lists_profile_choices(monkeypatch, tmp_path):
    app, data_file = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/api/plugins/jarvis-dashboard/v1/roles?token=test-token")

    assert response.status_code == 200
    payload = response.json()
    assert payload["storage"] == str(data_file)
    assert payload["writes_profile_configs"] is False
    assert "roles" in payload
    assert {role["role_id"] for role in payload["roles"]} >= {"orchestrator", "boss", "manager", "scout", "dev"}
    assert isinstance(payload["available_agents"], list)
    assert data_file.exists()


def test_roles_save_persists_mapping_without_touching_profile_config(monkeypatch, tmp_path):
    app, data_file = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    profile_config = tmp_path / "config.yaml"
    profile_config.write_text("original: true\n")

    body = {
        "roles": [
            {
                "role_id": "scout",
                "label": "Scout",
                "assigned_agent": "jarvis",
                "provider": "openai-codex",
                "model": "gpt-5.5",
                "status": "active",
                "platform": "dashboard",
                "notes": "research overlay only",
            }
        ]
    }
    response = client.post("/api/plugins/jarvis-dashboard/v1/roles?token=test-token", json=body)

    assert response.status_code == 200
    saved = json.loads(data_file.read_text())
    assert saved["roles"][0]["role_id"] == "scout"
    assert saved["roles"][0]["assigned_agent"] == "jarvis"
    assert profile_config.read_text() == "original: true\n"


def test_roles_rejects_path_like_agent_names_and_unknown_status(monkeypatch, tmp_path):
    app, _data_file = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    bad = {
        "roles": [
            {
                "role_id": "scout",
                "label": "Scout",
                "assigned_agent": "../jarvis-boss/config.yaml",
                "provider": "openai-codex",
                "model": "gpt-5.5",
                "status": "root",
            }
        ]
    }
    response = client.post("/api/plugins/jarvis-dashboard/v1/roles?token=test-token", json=bad)

    assert response.status_code == 422


def test_models_endpoint_returns_deduplicated_provider_model_pairs(monkeypatch, tmp_path):
    app, _data_file = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/api/plugins/jarvis-dashboard/v1/models?token=test-token")

    assert response.status_code == 200
    payload = response.json()
    assert "models" in payload
    assert isinstance(payload["models"], list)
    for item in payload["models"]:
        assert set(item) >= {"provider", "model", "source"}
