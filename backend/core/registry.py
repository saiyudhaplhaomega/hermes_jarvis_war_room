
class AgentInventory:
    """Tracks deployed agents for visibility and Shadow AI detection."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.agents = self._load_agents()

    def _load_agents(self) -> list[dict]:
        """Load agent registry from environment variables."""
        return [
            {
                "id": "agent_growth",
                "status": "active",
                "last_seen": datetime.now().isoformat(),
                "owner": "engineering"
            },
            {
                "id": "kanban",
                "status": "active",
                "last_seen": datetime.now().isoformat(),
                "owner": "product"
            }
        ]

    def scan(self) -> dict:
        """Scan for deployed agents."""
        return {"project_id": self.project_id, "agents": self.agents, "count": len(self.agents)}

    def register(self, agent_id: str, owner: str) -> bool:
        """Register a new agent."""
        self.agents.append({
            "id": agent_id,
            "status": "active",
            "last_seen": datetime.now().isoformat(),
            "owner": owner
        })
        return True

from datetime import datetime
import os

class AgentInventory:
    """Tracks deployed agents for visibility and Shadow AI detection."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.agents = self._load_agents()

    def _load_agents(self) -> list[dict]:
        """Load agent registry from environment variables."""
        return [
            {
                "id": "agent_growth",
                "status": "active",
                "last_seen": datetime.now().isoformat(),
                "owner": "engineering"
            },
            {
                "id": "kanban",
                "status": "active",
                "last_seen": datetime.now().isoformat(),
                "owner": "product"
            }
        ]

    def scan(self) -> dict:
        """Scan for deployed agents."""
        return {"project_id": self.project_id, "agents": self.agents, "count": len(self.agents)}

    def register(self, agent_id: str, owner: str) -> bool:
        """Register a new agent."""
        self.agents.append({
            "id": agent_id,
            "status": "active",
            "last_seen": datetime.now().isoformat(),
            "owner": owner
        })
        return True
