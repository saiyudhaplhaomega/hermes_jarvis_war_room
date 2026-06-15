"""Phase 2 tests: skill catalog + per-project assignment.

Per CLAUDE.md: failing test first (RED), then implement to GREEN.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"
CATALOG = REPO_ROOT / "state" / "skill_catalog.json"


def _load_app(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DASHBOARD_AGENT_SKILLS", str(tmp_path / "agent_skill_assignments.json"))
    monkeypatch.setenv("JARVIS_DASHBOARD_AGENT_PROPOSALS", str(tmp_path / "agent_proposals.json"))
    monkeypatch.setenv("JARVIS_DASHBOARD_REMOVED_AGENTS", str(tmp_path / "removed_agents.json"))
    monkeypatch.setenv("JARVIS_DASHBOARD_ROLE_MAPPINGS", str(tmp_path / "role_mappings.json"))
    monkeypatch.setenv("JARVIS_DASHBOARD_SKILL_CATALOG", str(tmp_path / "skill_catalog.json"))
    monkeypatch.setenv("JARVIS_DASHBOARD_DEV_TOKEN", "test-token")
    monkeypatch.setenv("JARVIS_DASHBOARD_QUERY_TOKEN_FALLBACK", "1")
    # Seed test profile dirs so agent validation passes
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    for slug in ("jarvis-frontend", "jarvis-backend", "jarvis-security-lead"):
        d = profiles_dir / slug
        d.mkdir()
        (d / "config.yaml").write_text(f"name: {slug}\nmodel: codex\nrole: {slug}\nworker_kind: api\n")
    # D-2026-06-09: agent_growth.py uses `core.config.PROFILE` which is
    # computed at import time. Re-point PROFILE to our test profiles dir
    # by setting HERMES_PROFILES_DIR before the import.
    monkeypatch.setenv("HERMES_PROFILES_DIR", str(profiles_dir))
    # Seed the test catalog with a known small set
    sample = {
        "version": 1,
        "updated_at": "2026-06-09T00:00:00Z",
        "skills": [
            {"id": "test/fe-skill", "name": "fe-skill", "description": "frontend test", "category": "engineering", "source_repo": "test/repo", "source_path": "fe/SKILL.md", "trust_tier": "T1", "departments": ["jarvis-frontend"], "mcp_servers": [], "review_status": "curated", "provenance": {"added_by": "t", "added_at": "2026-06-09T00:00:00Z"}, "hash": "h1"},
            {"id": "test/be-skill", "name": "be-skill", "description": "backend test", "category": "engineering", "source_repo": "test/repo", "source_path": "be/SKILL.md", "trust_tier": "T1", "departments": ["jarvis-backend"], "mcp_servers": [], "review_status": "curated", "provenance": {"added_by": "t", "added_at": "2026-06-09T00:00:00Z"}, "hash": "h2"},
            {"id": "test/sec-skill", "name": "sec-skill", "description": "security test", "category": "security", "source_repo": "test/repo", "source_path": "sec/SKILL.md", "trust_tier": "T1", "departments": ["jarvis-security-lead"], "mcp_servers": [], "review_status": "curated", "provenance": {"added_by": "t", "added_at": "2026-06-09T00:00:00Z"}, "hash": "h3"},
        ],
        "sources": [{"repo": "test/repo", "tier": "T1", "kind": "curated", "license": "MIT", "trust_tier": "T1"}],
        "summary": {"total_skills": 3, "by_trust_tier": {"T1": 3, "T2": 0}, "by_source": {"test/repo": 3}, "by_category": {"engineering": 2, "security": 1}},
    }
    (tmp_path / "skill_catalog.json").write_text(json.dumps(sample))
    # Reload modules
    for name in list(sys.modules):
        if name == "server" or name.startswith("api.agent_growth") or name.startswith("api.roles"):
            sys.modules.pop(name, None)
    sys.path.insert(0, str(BACKEND))
    import server
    return server.app


def test_catalog_get_returns_all_skills(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    r = client.get("/api/plugins/jarvis-dashboard/v1/catalog?token=test-token")
    assert r.status_code == 200
    data = r.json()
    assert data["writes_profile_configs"] is False
    assert data["summary"]["total_skills"] == 3
    assert len(data["skills"]) == 3


def test_catalog_filter_by_trust_tier(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    r = client.get("/api/plugins/jarvis-dashboard/v1/catalog?trust_tier=T2&token=test-token")
    assert r.status_code == 200
    assert r.json()["skills"] == []


def test_catalog_filter_by_department(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    r = client.get("/api/plugins/jarvis-dashboard/v1/catalog/by-department/jarvis-frontend?token=test-token")
    assert r.status_code == 200
    data = r.json()
    assert data["department"] == "jarvis-frontend"
    assert data["count"] == 1
    assert data["skills"][0]["id"] == "test/fe-skill"


def test_catalog_search_q(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    r = client.get("/api/plugins/jarvis-dashboard/v1/catalog?q=security&token=test-token")
    assert r.status_code == 200
    skills = r.json()["skills"]
    assert len(skills) == 1
    assert skills[0]["id"] == "test/sec-skill"


def test_catalog_never_writes_profile_configs(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    # All catalog responses must include writes_profile_configs: false
    endpoints = [
        ("GET", "/api/plugins/jarvis-dashboard/v1/catalog?token=test-token"),
        ("GET", "/api/plugins/jarvis-dashboard/v1/catalog/by-department/jarvis-backend?token=test-token"),
        ("POST", "/api/plugins/jarvis-dashboard/v1/catalog/refresh?token=test-token"),
    ]
    for method, url in endpoints:
        r = client.get(url) if method == "GET" else client.post(url)
        assert r.status_code == 200, f"failed: {method} {url} -> {r.status_code} {r.text}"
        assert r.json()["writes_profile_configs"] is False, f"invariant broken: {url}"


def test_save_skill_assignment_by_project(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    payload = {
        "project": "war-room",
        "agent": "jarvis-frontend",
        "skills": ["test/fe-skill"],
        "notes": "phase 2 test"
    }
    r = client.post("/api/plugins/jarvis-dashboard/v1/agents/skills-by-project?token=test-token", json=payload)
    assert r.status_code == 200, f"got {r.status_code} {r.text}"
    data = r.json()
    assert data["writes_profile_configs"] is False
    assert data["project"] == "war-room"
    assert data["agent"] == "jarvis-frontend"
    assert data["skills"] == ["test/fe-skill"]


def test_save_skill_assignment_by_project_unknown_agent(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    payload = {"project": "war-room", "agent": "nope-not-real", "skills": []}
    r = client.post("/api/plugins/jarvis-dashboard/v1/agents/skills-by-project?token=test-token", json=payload)
    assert r.status_code == 422
    assert "unknown agent" in r.json()["detail"]


def test_save_skill_assignment_by_project_unknown_skill(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    payload = {"project": "war-room", "agent": "jarvis-frontend", "skills": ["nope/not-a-skill"]}
    r = client.post("/api/plugins/jarvis-dashboard/v1/agents/skills-by-project?token=test-token", json=payload)
    assert r.status_code == 422
    assert "unknown skills" in r.json()["detail"]


def test_get_skill_assignment_by_project(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    # Save first
    client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/skills-by-project?token=test-token",
        json={"project": "war-room", "agent": "jarvis-frontend", "skills": ["test/fe-skill"]},
    )
    # Then read back
    r = client.get("/api/plugins/jarvis-dashboard/v1/agents/jarvis-frontend/skills-by-project?project=war-room&token=test-token")
    assert r.status_code == 200
    data = r.json()
    assert data["skills"] == ["test/fe-skill"]


def test_per_project_isolation(monkeypatch, tmp_path):
    """Saving a skill for project A must not affect project B."""
    from fastapi.testclient import TestClient
    app = _load_app(monkeypatch, tmp_path)
    client = TestClient(app)
    # Same agent, two different projects, two different skills
    r1 = client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/skills-by-project?token=test-token",
        json={"project": "project-a", "agent": "jarvis-frontend", "skills": ["test/fe-skill"]},
    )
    r2 = client.post(
        "/api/plugins/jarvis-dashboard/v1/agents/skills-by-project?token=test-token",
        json={"project": "project-b", "agent": "jarvis-frontend", "skills": ["test/be-skill"]},
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Read back
    a = client.get("/api/plugins/jarvis-dashboard/v1/agents/jarvis-frontend/skills-by-project?project=project-a&token=test-token").json()
    b = client.get("/api/plugins/jarvis-dashboard/v1/agents/jarvis-frontend/skills-by-project?project=project-b&token=test-token").json()
    assert a["skills"] == ["test/fe-skill"]
    assert b["skills"] == ["test/be-skill"]


def test_catalog_seeded_skill_count():
    """The live state/skill_catalog.json must have 64 skills and 7 sources."""
    data = json.loads(CATALOG.read_text())
    assert data["summary"]["total_skills"] == 64
    assert len(data["sources"]) == 7
    # 4 T1 + 3 T2
    assert data["summary"]["by_trust_tier"]["T1"] >= 1
    assert data["summary"]["by_trust_tier"]["T2"] >= 1


def test_skill_ids_are_unique():
    data = json.loads(CATALOG.read_text())
    ids = [s["id"] for s in data["skills"]]
    assert len(ids) == len(set(ids)), "duplicate skill ids"


def test_every_skill_has_required_fields():
    data = json.loads(CATALOG.read_text())
    required = {"id", "name", "category", "source_repo", "source_path", "trust_tier", "description", "departments", "mcp_servers", "review_status", "provenance", "hash"}
    for s in data["skills"]:
        missing = required - set(s.keys())
        assert not missing, f"skill {s.get('id')!r} missing {missing}"
