"""
CrewAI Departments for Hermes Jarvis War Room.

Adds declarative agent roles (e.g., Engineering Lead, Product Manager).
"""
from __future__ import annotations

from crewai import Agent, Task, Crew, Process
from typing import Optional, Literal

class CrewAIDepartment:
    """Role-based department using CrewAI."""

    def __init__(self, department: Literal["engineering", "product", "marketing", "finance"]):
        self.department = department
        self.agents = self._load_agents()

    def _load_agents(self) -> list[Agent]:
        """Load department-specific agents."""
        return [
            Agent(
                role=f"{self.department.capitalize()} Lead",
                goal=f"Coordinate {self.department} tasks",
                backstory=f"Expert in {self.department} workflows with 10+ years of experience.",
                llm="codex/gpt-5.5",
                verbose=True
            ),
            Agent(
                role=f"{self.department.capitalize()} Specialist",
                goal=f"Execute {self.department} tasks",
                backstory=f"Skilled in {self.department} tools and best practices.",
                llm="minimax/abab6.5s-chat",
                verbose=True
            )
        ]

    def kickoff(self, task: str) -> str:
        """Run a task with the department crew."""
        crew = Crew(
            agents=self.agents,
            tasks=[Task(description=task)],
            process=Process.sequential
        )
        return crew.kickoff()

# Example usage
dept = CrewAIDepartment("engineering")
result = dept.kickoff("Refactor agent_growth.py to add retry logic")
print(result)
