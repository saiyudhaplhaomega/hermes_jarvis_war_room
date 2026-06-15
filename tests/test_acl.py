import pytest
from backend.core.acl import ZeroTrustHandoff

def test_zero_trust_handoff():
    handoff = ZeroTrustHandoff("test_project")
    task_id = "t_123"
    signature = handoff.sign_handoff("engineering", "product", task_id)
    assert handoff.verify_handoff("engineering", "product", task_id, signature)
    assert not handoff.verify_handoff("engineering", "product", "t_456", signature)
