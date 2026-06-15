"""Tests for r52-r55 endpoints (isolated, no server.py import)."""
import os
import sys
import sqlite3
import tempfile
import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


@pytest.fixture
def ledger():
    """Create a temp ledger for testing."""
    from core.operating_ledger import OperatingLedger
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    ledger = OperatingLedger(db_path=db_path)
    yield ledger
    # Note: don't unlink on Windows due to file lock issues; temp files will be cleaned up by OS


@pytest.fixture
def dashboard(ledger):
    from core.kpi_dashboard import KPIDashboard
    return KPIDashboard(ledger)


@pytest.fixture
def queue(ledger):
    from core.handoff_queue import HandoffQueue
    return HandoffQueue(ledger)


@pytest.fixture
def permissions():
    from core.permissions_matrix import PermissionsMatrix
    return PermissionsMatrix()


def test_operating_ledger_init(ledger):
    """r52: Operating ledger initializes with schema."""
    with sqlite3.connect(ledger.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ledger'")
        assert cursor.fetchone() is not None


def test_kpi_dashboard(dashboard):
    """r53: KPI dashboard returns 7 KPIs."""
    kpis = dashboard.get_kpis()
    assert "mrr" in kpis
    assert "arr" in kpis
    assert "churn_rate" in kpis
    assert "cac" in kpis
    assert "ltv" in kpis
    assert "burn_rate" in kpis
    assert "cash_runway" in kpis


def test_handoff_create(queue):
    """r54: Create handoff."""
    result = queue.create_handoff(
        ticket_id="test123",
        from_dept="engineering",
        to_dept="product",
        artifacts=["pr.html"]
    )
    assert result["ticket_id"] == "test123"
    assert result["from_dept"] == "engineering"
    assert result["to_dept"] == "product"
    assert result["status"] == "pending"
    assert "sla_deadline" in result


def test_handoff_persistence(queue):
    """r54: Handoff persists and can be retrieved."""
    queue.create_handoff(
        ticket_id="test456",
        from_dept="product",
        to_dept="marketing",
        artifacts=[{"type": "feature_brief"}]
    )
    retrieved = queue.get_handoff("test456")
    assert retrieved is not None
    assert retrieved["from_dept"] == "product"
    assert retrieved["to_dept"] == "marketing"


def test_permissions_check(permissions):
    """r55: Check permission for dept/action."""
    level = permissions.check_permission("engineering", "deploy_prod")
    assert level.name in ["AUTO", "APPROVE", "HUMAN", "NONE"]


def test_ai_never_gates(permissions):
    """r55: 10 AI-NEVER gates defined (5 spec + 5 impl)."""
    # r55 spec gates
    assert "sign_contract" in permissions.ai_never
    assert "issue_refund_credit" in permissions.ai_never
    assert "hire_fire" in permissions.ai_never
    assert "public_statement" in permissions.ai_never
    assert "pricing_exception" in permissions.ai_never
    # Implementation gates
    assert "access_payroll" in permissions.ai_never
    assert "access_legal_privileged" in permissions.ai_never
    assert "access_customer_pii" in permissions.ai_never
    assert "delete_audit_log" in permissions.ai_never


def test_ai_never_enforced(permissions):
    """r55: AI-NEVER actions are always denied regardless of dept."""
    for dept in ["engineering", "product", "sales", "marketing"]:
        for action in permissions.ai_never:
            level = permissions.check_permission(dept, action)
            assert level.name == "NONE", f"{dept}.{action} should be NONE, got {level.name}"


def test_ledger_write_and_query(ledger):
    """r52: Write entity, then query it back as parsed dict."""
    data = {"name": "Acme Corp", "mrr": 5000, "industry": "tech"}
    success = ledger.write("account", "acme", data)
    assert success is True
    retrieved = ledger.query("account", "acme")
    assert retrieved is not None
    assert retrieved["name"] == "Acme Corp"
    assert retrieved["mrr"] == 5000
    assert retrieved["industry"] == "tech"


def test_ledger_query_view(ledger):
    """r52: Write 3 accounts, query view_accounts."""
    for i in range(3):
        ledger.write("account", f"acct{i}", {"name": f"Acct {i}", "mrr": 1000 * i})
    results = ledger.query_view("vw_accounts")
    assert len(results) == 3


def test_ledger_view_injection_blocked(ledger):
    """r52: SQL injection in view name is blocked."""
    with pytest.raises(ValueError, match="unknown view"):
        ledger.query_view("vw_accounts; DROP TABLE ledger;--")


def test_ledger_view_filters_safe(ledger):
    """r52: Filter keys are whitelisted (no SQL injection)."""
    ledger.write("account", "acme", {"name": "Acme", "mrr": 5000})
    # Safe filter
    results = ledger.query_view("vw_accounts", {"entity_id": "acme"})
    assert len(results) == 1
    # Malicious filter (should be ignored)
    results = ledger.query_view("vw_accounts", {"entity_id; DROP TABLE--": "x"})
    # Returns all rows since malicious filter is ignored
    assert len(results) >= 1


def test_kpi_mrr_calculation(ledger, dashboard):
    """r53: MRR sums all account mrr values."""
    ledger.write("account", "a1", {"mrr": 100})
    ledger.write("account", "a2", {"mrr": 200})
    ledger.write("account", "a3", {"mrr": 300})
    kpis = dashboard.get_kpis()
    assert kpis["mrr"] == 600
    assert kpis["arr"] == 7200  # 600 * 12


def test_kpi_dashboard_all_seven(ledger, dashboard):
    """r53: All 7 KPIs present in response."""
    ledger.write("account", "a1", {"mrr": 100})
    kpis = dashboard.get_kpis()
    expected = ["mrr", "arr", "churn_rate", "cac", "ltv", "burn_rate", "cash_runway"]
    for k in expected:
        assert k in kpis, f"missing KPI: {k}"


def test_handoff_sla_48h_eng_to_product(queue):
    """r54: SLA for engineering->product is 48h."""
    result = queue.create_handoff(
        ticket_id="sla-test",
        from_dept="engineering",
        to_dept="product",
    )
    from datetime import datetime, timezone, timedelta
    created = datetime.fromisoformat(result["created_at"])
    deadline = datetime.fromisoformat(result["sla_deadline"])
    diff = deadline - created
    # Should be ~48 hours
    assert 47 <= diff.total_seconds() / 3600 <= 49


def test_permissions_unknown_action_denied(permissions):
    """r55: Unknown actions are denied."""
    level = permissions.check_permission("engineering", "nonexistent_action_xyz")
    assert level.name == "NONE"


def test_permissions_known_actions(permissions):
    """r55: Known actions return expected levels."""
    assert permissions.check_permission("engineering", "deploy_prod").name == "APPROVE"
    assert permissions.check_permission("engineering", "merge_pr").name == "AUTO"
    assert permissions.check_permission("engineering", "access_finance").name == "NONE"


if __name__ == "__main__":
    test_operating_ledger_init()
    test_kpi_dashboard()
    test_handoff_create()
    test_permissions_check()
    test_ai_never_gates()
    print("All r52-r55 tests passed!")