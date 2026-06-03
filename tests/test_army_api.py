import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def _load_app(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DASHBOARD_DEV_TOKEN", "test-token")
    monkeypatch.setenv("JARVIS_DASHBOARD_ARMY_STATE", str(tmp_path / "army_state.json"))
    monkeypatch.setenv("JARVIS_DASHBOARD_ARMY_RUNS", str(tmp_path / "army_runs"))
    monkeypatch.setenv("JARVIS_DASHBOARD_ARMY_DISABLE_EXEC", "1")
    for name in list(sys.modules):
        if name == "server" or name.startswith("api.army"):
            sys.modules.pop(name, None)
    import server
    return server.app, tmp_path


def test_army_workers_report_available_and_unavailable_without_profile_writes(monkeypatch, tmp_path):
    app, _root = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/api/plugins/jarvis-dashboard/v1/army/workers?token=test-token")

    assert response.status_code == 200
    payload = response.json()
    assert payload["writes_profile_configs"] is False
    workers = {worker["id"]: worker for worker in payload["workers"]}
    assert {"claude", "codex", "minimax"} <= set(workers)
    assert workers["claude"]["kind"] == "cli"
    assert isinstance(workers["codex"]["available"], bool)


def test_army_dry_run_lifecycle_is_dashboard_local(monkeypatch, tmp_path):
    app, root = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    profile_config = tmp_path / "config.yaml"
    profile_config.write_text("original: true\n")

    created = client.post(
        "/api/plugins/jarvis-dashboard/v1/army/runs?token=test-token",
        json={"worker": "claude", "task": "write a harmless status note", "repo": str(root), "dry_run": True},
    )

    assert created.status_code == 200
    run = created.json()["run"]
    assert run["worker"] == "claude"
    assert run["status"] in {"completed", "needs_review"}
    assert run["writes_profile_configs"] is False
    assert profile_config.read_text() == "original: true\n"

    listed = client.get("/api/plugins/jarvis-dashboard/v1/army/runs?token=test-token")
    assert listed.status_code == 200
    assert any(item["run_id"] == run["run_id"] for item in listed.json()["runs"])

    logs = client.get(f"/api/plugins/jarvis-dashboard/v1/army/runs/{run['run_id']}/logs?token=test-token")
    assert logs.status_code == 200
    assert "DRY RUN" in logs.json()["logs"]

    diff = client.get(f"/api/plugins/jarvis-dashboard/v1/army/runs/{run['run_id']}/diff?token=test-token")
    assert diff.status_code == 200
    assert "final.txt" in diff.json()["diff"]


def test_army_reject_and_rerun_preserve_feedback(monkeypatch, tmp_path):
    app, root = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    run = client.post(
        "/api/plugins/jarvis-dashboard/v1/army/runs?token=test-token",
        json={"worker": "claude", "task": "first attempt", "repo": str(root), "dry_run": True},
    ).json()["run"]

    rejected = client.post(
        f"/api/plugins/jarvis-dashboard/v1/army/runs/{run['run_id']}/reject?token=test-token",
        json={"reason": "missing smoke test evidence"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["run"]["status"] == "rejected"
    assert rejected.json()["run"]["reject_reason"] == "missing smoke test evidence"

    rerun = client.post(f"/api/plugins/jarvis-dashboard/v1/army/runs/{run['run_id']}/rerun?token=test-token")
    assert rerun.status_code == 200
    new_run = rerun.json()["run"]
    assert new_run["parent_run_id"] == run["run_id"]
    assert "Previous reject reason: missing smoke test evidence" in new_run["task"]


def test_army_rejects_path_like_run_ids(monkeypatch, tmp_path):
    app, _root = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/api/plugins/jarvis-dashboard/v1/army/runs/../../../etc/passwd/logs?token=test-token")

    assert response.status_code in {400, 404}


def test_army_approve_is_state_only_not_merge(monkeypatch, tmp_path):
    app, root = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    run = client.post(
        "/api/plugins/jarvis-dashboard/v1/army/runs?token=test-token",
        json={"worker": "claude", "task": "approval packet", "repo": str(root), "dry_run": True},
    ).json()["run"]

    approved = client.post(f"/api/plugins/jarvis-dashboard/v1/army/runs/{run['run_id']}/approve?token=test-token")

    assert approved.status_code == 200
    payload = approved.json()
    assert payload["run"]["status"] == "approved"
    assert payload["writes_profile_configs"] is False
    assert payload["merged"] is False
