"""Route tests for c100-r17 wired OS endpoints."""
import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient
import pytest
from backend.server import app, agent_os, human_gates, fact_store, policy_attestor
from core.agent_os_primitives import Capability
from auth.dependencies import get_current_user


def override_get_current_user():
    return "saiyu"


app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    fd, db = tempfile.mkstemp(suffix=".db")
    os.close(fd)


def setup_module(module):
    agent_os.create_namespace("test")
    agent_os.grant_capability("test", "agent-1", Capability.READ_LEDGER)


def test_agent_os_namespace():
    r = client.post("/api/plugins/jarvis-dashboard/v1/agent-os/namespace", params={"name": "unique-ns-" + str(uuid.uuid4())[:8], "department": "engineering"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_agent_os_capability():
    client.post("/api/plugins/jarvis-dashboard/v1/agent-os/namespace", params={"name": "eng", "department": "engineering"})
    r = client.post("/api/plugins/jarvis-dashboard/v1/agent-os/capability", params={"namespace": "eng", "agent_id": "a1", "capability": "READ_LEDGER"})
    assert r.status_code == 200
    r2 = client.get("/api/plugins/jarvis-dashboard/v1/agent-os/capability", params={"namespace": "eng", "agent_id": "a1", "capability": "READ_LEDGER"})
    assert r2.json()["has"] is True


def test_human_gate_flow():
    r = client.post("/api/plugins/jarvis-dashboard/v1/human-gate", params={"dept": "engineering", "agent_id": "a1", "action": "deploy_prod", "justification": "hotfix"})
    assert r.status_code == 200
    gate_id = r.json()["id"]
    r2 = client.get("/api/plugins/jarvis-dashboard/v1/human-gate/pending", params={"dept": "engineering"})
    assert any(g["id"] == gate_id for g in r2.json())
    r3 = client.post(f"/api/plugins/jarvis-dashboard/v1/human-gate/{gate_id}/approve", params={"human_id": "saiyu", "reason": "ok"})
    assert r3.json()["state"] == "approved"


def test_facts_flow():
    subj = "Jarvis-" + str(uuid.uuid4())[:6]
    r = client.post("/api/plugins/jarvis-dashboard/v1/facts", params={"subject": subj, "predicate": "is", "obj": "OS", "source": "council"})
    assert r.status_code == 200
    r2 = client.get("/api/plugins/jarvis-dashboard/v1/facts", params={"subject": subj})
    assert len(r2.json()) == 1
    r3 = client.get("/api/plugins/jarvis-dashboard/v1/facts/search", params={"q": subj})
    assert len(r3.json()) >= 1


def test_policy_attest_auto():
    client.post("/api/plugins/jarvis-dashboard/v1/agent-os/namespace", params={"name": "engineering", "department": "engineering"})
    r = client.post("/api/plugins/jarvis-dashboard/v1/policy/attest", params={"agent_id": "a1", "action": "merge_pr", "namespace": "engineering", "purpose": "routine"})
    assert r.status_code == 200
    assert r.json()["allowed"] is True


def test_policy_attest_ai_never():
    client.post("/api/plugins/jarvis-dashboard/v1/agent-os/namespace", params={"name": "engineering", "department": "engineering"})
    r = client.post("/api/plugins/jarvis-dashboard/v1/policy/attest", params={"agent_id": "a1", "action": "sign_contract", "namespace": "engineering", "purpose": "deal"})
    assert r.status_code == 403
