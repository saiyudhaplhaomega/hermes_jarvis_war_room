"""Tests for runtime policy attestations (c100-r15)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from core.agent_os_primitives import AgentOS, Capability
from core.human_gates import HumanGateRegistry
from core.permissions_matrix import PermissionsMatrix
from core.policy_attestor import PolicyAttestor


def make_attestor(tmp_db):
    agent_os = AgentOS(db_path=Path(tmp_db).with_suffix(".os.db"))
    gates = HumanGateRegistry(db_path=Path(tmp_db).with_suffix(".gates.db"))
    perms = PermissionsMatrix()
    return PolicyAttestor(
        db_path=Path(tmp_db).with_suffix(".att.db"),
        permissions=perms,
        agent_os=agent_os,
        gates=gates,
    )


def test_auto_action_allowed():
    fd, db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    att = make_attestor(db)
    att.agent_os.create_namespace("engineering")
    att.agent_os.grant_capability("engineering", "agent-1", Capability.WRITE_LEDGER)
    att.agent_os.set_quota("engineering", max_calls_per_minute=10)
    allowed, reason, a = att.can_execute("agent-1", "merge_pr", "engineering", "routine merge")
    assert allowed
    assert a is not None
    assert a.policy_version == "c100-r15"


def test_ai_never_blocked():
    fd, db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    att = make_attestor(db)
    att.agent_os.create_namespace("engineering")
    att.agent_os.grant_capability("engineering", "agent-1", Capability.ACCESS_VAULT)
    att.agent_os.set_quota("engineering", max_calls_per_minute=10)
    allowed, reason, a = att.can_execute("agent-1", "sign_contract", "engineering", "deal")
    assert not allowed
    assert a is None
    assert "NEVER" in reason or "unknown" in reason.lower()


def test_approve_action_requires_gate():
    fd, db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    att = make_attestor(db)
    att.agent_os.create_namespace("engineering")
    att.agent_os.grant_capability("engineering", "agent-1", Capability.DEPLOY_PROD)
    att.agent_os.set_quota("engineering", max_calls_per_minute=10)
    allowed, reason, a = att.can_execute("agent-1", "deploy_prod", "engineering", "hotfix")
    assert not allowed
    assert "approval required" in reason


def test_approve_auto_approved_for_system():
    fd, db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    att = make_attestor(db)
    att.agent_os.create_namespace("engineering")
    att.agent_os.grant_capability("engineering", "agent-1", Capability.DEPLOY_PROD)
    att.agent_os.set_quota("engineering", max_calls_per_minute=10)
    allowed, reason, a = att.can_execute(
        "agent-1", "deploy_prod", "engineering", "hotfix", delegator="system"
    )
    assert allowed
    assert a.approval_id is not None


def test_verify_attestation():
    fd, db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    att = make_attestor(db)
    att.agent_os.create_namespace("engineering")
    att.agent_os.grant_capability("engineering", "agent-1", Capability.WRITE_LEDGER)
    att.agent_os.set_quota("engineering", max_calls_per_minute=10)
    allowed, reason, a = att.can_execute("agent-1", "merge_pr", "engineering", "routine merge")
    ok, msg = att.verify_attestation(a.action_id)
    assert ok
    assert msg == "ok"


def test_finalize_output():
    fd, db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    att = make_attestor(db)
    att.agent_os.create_namespace("engineering")
    att.agent_os.grant_capability("engineering", "agent-1", Capability.WRITE_LEDGER)
    att.agent_os.set_quota("engineering", max_calls_per_minute=10)
    allowed, reason, a = att.can_execute("agent-1", "merge_pr", "engineering", "routine merge")
    assert att.finalize_output(a.action_id, {"status": "deployed"})
    ok, msg = att.verify_attestation(a.action_id)
    assert ok
