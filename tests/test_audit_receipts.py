"""Tests for signed audit receipts (c100-r05)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from observability.audit_log import AuditLog


def test_audit_receipts_and_chain():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    log = AuditLog(db_path=db_path, hmac_secret="test-secret")
    log.log_action("u1", "deploy", "service", "svc-1", {"ref": "abc"}, trust_level=5)
    log.log_action("u2", "approve", "decision", "d-1", trust_level=8)
    logs = log.query_logs()
    assert len(logs) == 2
    assert logs[0]["trust_level"] == 5
    assert logs[1]["trust_level"] == 8
    assert logs[1]["previous_hash"] == logs[0]["row_hash"]
    ok, issues = log.verify_chain()
    assert ok
    assert issues == []


def test_tamper_detection():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    log = AuditLog(db_path=db_path, hmac_secret="test-secret")
    log.log_action("u1", "deploy", "service", "svc-1")
    # Tamper with the database directly
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE audit_log SET action='hacked'")
        conn.commit()
    ok, issues = log.verify_chain()
    assert not ok
    assert len(issues) >= 1


def test_trust_level_validation():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    log = AuditLog(db_path=db_path, hmac_secret="test-secret")
    try:
        log.log_action("u1", "x", "y", "z", trust_level=11)
        assert False
    except ValueError:
        pass
    try:
        log.log_action("u1", "x", "y", "z", trust_level=0)
        assert False
    except ValueError:
        pass
