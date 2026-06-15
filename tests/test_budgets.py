import pytest
from backend.core.budgets import CostOptimizer

def test_cost_optimizer():
    optimizer = CostOptimizer()
    provider, model = optimizer.route("Security audit", budget=0.01)
    assert provider == "minimax"
    assert model == "abab6.5s-chat"
