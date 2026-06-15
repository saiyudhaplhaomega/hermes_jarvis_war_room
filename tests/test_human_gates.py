"""Tests for human-in-the-loop gating (c100-r07)."""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from core.human_gates import HumanGateRegistry, HumanGateState


def test_request_approve_deny():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    reg = HumanGateRegistry(db_path=Path(db_path))
    gate = reg.request("engineering", "agent-1", "deploy:prod", "critical fix")
    assert gate.state == HumanGateState.PENDING
    pending = reg.list_pending("engineering")
    assert len(pending) == 1
    approved = reg.approve(gate.id, "saiyu", "verified")
    assert approved.state == HumanGateState.APPROVED
    assert approved.trust_level == 8


def test_deny_gate():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    reg = HumanGateRegistry(db_path=Path(db_path))
    gate = reg.request("engineering", "agent-1", "delete:database", "oops")
    denied = reg.deny(gate.id, "saiyu", "too risky")
    assert denied.state == HumanGateState.DENIED
    assert denied.decision_reason == "too risky"


def test_escalation_timeout():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    reg = HumanGateRegistry(db_path=Path(db_path))
    gate = reg.request(
        "engineering", "agent-1", "restart:api", "needed",
        timeout_seconds=600, escalation_after_seconds=300,
    )
    near_future = gate.requested_at + timedelta(seconds=400)
    state = reg.check_timeout_or_escalate(gate.id, now=near_future)
    assert state == HumanGateState.ESCALATED
    far_future = gate.requested_at + timedelta(seconds=700)
    state = reg.check_timeout_or_escalate(gate.id, now=far_future)
    assert state == HumanGateState.TIMEOUT


def test_audit_receipts_emitted():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    reg = HumanGateRegistry(db_path=Path(db_path))
    gate = reg.request("finance", "agent-2", "issue:refund", "customer dispute")
    reg.approve(gate.id, "saiyu")
    logs = reg.audit.query_logs()
    events = []
    import json
    for l in logs:
        meta = l.get("metadata")
        if meta:
            if isinstance(meta, str):
                meta = json.loads(meta)
            events.append(meta.get("event"))
    assert "requested" in events
    assert "approved" in events
