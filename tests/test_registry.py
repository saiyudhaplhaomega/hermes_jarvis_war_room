import pytest
from backend.core.registry import AgentInventory

def test_agent_inventory():
    inventory = AgentInventory("test_project")
    result = inventory.scan()
    assert result["count"] == 2
    assert result["agents"][0]["id"] == "agent_growth"

def test_register_agent():
    inventory = AgentInventory("test_project")
    assert inventory.register("new_agent", "engineering")
    assert inventory.scan()["count"] == 3
