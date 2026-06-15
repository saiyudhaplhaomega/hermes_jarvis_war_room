import pytest
from backend.core.audit import EthicsReviewBoard, BiasAuditor

def test_ethics_review_board():
    board = EthicsReviewBoard("test_project")
    assert board.review("Delete user data", "high")  # Should notify board
    assert board.review("Refactor code", "low")     # Should pass

def test_bias_auditor():
    auditor = BiasAuditor("test_project")
    results = auditor.audit()
    assert results["passed"] >= 1
    assert results["bias_issues"] == 0  # "Hire male engineer" should be rejected
