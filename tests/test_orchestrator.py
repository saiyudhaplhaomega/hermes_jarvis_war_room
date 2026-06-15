import pytest
from backend.core.orchestrator import OrchestrationEngine

def test_supervisor_pattern():
    engine = OrchestrationEngine(pattern="supervisor")
    result = engine.execute("Refactor agent_growth.py")
    assert "success" in result

def test_swarm_pattern():
    engine = OrchestrationEngine(pattern="swarm")
    result = engine.execute("Debug kanban.py")
    assert len(result.split(";")) >= 1
