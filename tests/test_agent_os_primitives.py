"""Tests for backend/core/agent_os_primitives.py (c100-r03)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from core.agent_os_primitives import AgentOS, Capability, Namespace, Quota, Taint


@pytest.fixture
def os_inst():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    inst = AgentOS(db_path=Path(db_path))
    yield inst
    # Windows file lock: don't unlink


def test_grant_and_check_capability(os_inst):
    os_inst.create_namespace("ns1", "engineering", "proj-a")
    assert os_inst.grant_capability("ns1", "agent-1", Capability.READ_LEDGER)
    assert os_inst.has_capability("ns1", "agent-1", Capability.READ_LEDGER)
    assert not os_inst.has_capability("ns1", "agent-1", Capability.WRITE_LEDGER)


def test_capability_expires(os_inst):
    os_inst.create_namespace("ns1")
    past = "2020-01-01T00:00:00+00:00"
    os_inst.grant_capability("ns1", "agent-1", Capability.READ_LEDGER, expires_at=past)
    assert not os_inst.has_capability("ns1", "agent-1", Capability.READ_LEDGER)


def test_revoke_capability(os_inst):
    os_inst.create_namespace("ns1")
    os_inst.grant_capability("ns1", "agent-1", Capability.READ_LEDGER)
    assert os_inst.revoke_capability("ns1", "agent-1", Capability.READ_LEDGER)
    assert not os_inst.has_capability("ns1", "agent-1", Capability.READ_LEDGER)


def test_namespace_listing(os_inst):
    os_inst.create_namespace("eng", "engineering", "*")
    os_inst.create_namespace("prod", "product", "*")
    ns = os_inst.list_namespaces("engineering")
    assert any(n["name"] == "eng" for n in ns)
    assert not any(n["name"] == "prod" for n in ns)


def test_quota_allow_and_block(os_inst):
    os_inst.create_namespace("ns1")
    os_inst.set_quota("ns1", max_calls_per_minute=2, max_tokens_per_hour=1000, max_spend_per_day_usd=1.0)
    ok, msg = os_inst.check_quota("ns1", calls=1)
    assert ok
    os_inst.record_usage("ns1", calls=1)
    ok, msg = os_inst.check_quota("ns1", calls=2)
    assert not ok
    assert "call quota" in msg


def test_taint_and_vault(os_inst):
    os_inst.create_namespace("finance")
    os_inst.apply_taint("ledger_row", "row-1", Taint.FINANCE, "finance")
    assert "FINANCE" in os_inst.get_taint("ledger_row", "row-1")
    # Without ACCESS_VAULT, cannot read FINANCE vault secret
    os_inst.vault_write("finance", "api_key", "secret123", Taint.FINANCE, "admin")
    assert os_inst.vault_read("finance", "api_key", []) is None
    assert os_inst.vault_read("finance", "api_key", [Capability.ACCESS_VAULT]) == "secret123"


def test_vault_key_validation(os_inst):
    os_inst.create_namespace("ns1")
    assert not os_inst.vault_write("ns1", "bad key!", "x", Taint.PUBLIC, "admin")
    assert os_inst.vault_write("ns1", "good.key", "x", Taint.PUBLIC, "admin")


def test_audit_logging(os_inst):
    os_inst.create_namespace("ns1")
    os_inst.log_audit("ns1", "agent-1", "deploy", entity_type="service", entity_id="svc-1")
    logs = os_inst.query_audit("ns1")
    assert len(logs) == 1
    assert logs[0]["action"] == "deploy"


def test_outcomes(os_inst):
    os_inst.create_namespace("ns1")
    os_inst.record_outcome("ns1", "agent-1", "task-1", "success", score=0.95)
    outcomes = os_inst.get_outcomes(namespace="ns1")
    assert len(outcomes) == 1
    assert outcomes[0]["status"] == "success"
    assert outcomes[0]["score"] == 0.95
