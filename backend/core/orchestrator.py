"""Multi-agent orchestration engine (Supervisor/Worker + Swarm patterns)."""

from typing import Dict, Any
import os

class OrchestrationEngine:
    """Orchestrates multi-agent workflows using Supervisor/Worker or Swarm patterns."""

    def __init__(self, pattern: str = "supervisor"):
        self.pattern = pattern
        self.agents = self._load_agents()

    def _load_agents(self) -> Dict[str, Dict[str, Any]]:
        """Load agent configurations from environment variables."""
        return {
            "supervisor": {
                "role": "Coordinator",
                "llm": os.getenv("SUPERVISOR_LLM", "codex/gpt-5.5"),
                "max_workers": int(os.getenv("SUPERVISOR_MAX_WORKERS", "5"))
            },
            "worker": {
                "role": "Specialist",
                "llm": os.getenv("WORKER_LLM", "minimax/abab6.5s-chat"),
                "skills": os.getenv("WORKER_SKILLS", "coding,debugging").split(",")
            }
        }

    def execute(self, task: str) -> str:
        """Execute task using the selected orchestration pattern."""
        if self.pattern == "supervisor":
            return self._supervisor_pattern(task)
        elif self.pattern == "swarm":
            return self._swarm_pattern(task)
        else:
            raise ValueError(f"Unknown pattern: {self.pattern}")

    def _supervisor_pattern(self, task: str) -> str:
        """Supervisor delegates to best worker."""
        worker = self._route_task(task)
        return worker.execute(task)

    def _swarm_pattern(self, task: str) -> str:
        """Swarm agents collaborate in parallel."""
        results = []
        for agent in self.agents.values():
            if agent["role"] == "Specialist":
                results.append(agent.execute(task))
        return "; ".join(results)

    def _route_task(self, task: str) -> Any:
        """Route task to best worker based on skills."""
        for agent in self.agents.values():
            if agent["role"] == "Specialist" and any(skill in task for skill in agent["skills"]):
                return agent
        return self.agents["worker"]  # Fallback
