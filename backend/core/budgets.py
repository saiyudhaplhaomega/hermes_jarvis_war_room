"""
ROICalculator for multi-agent workflows.

Usage:
    from backend.core.budgets import ROICalculator
    roi = ROICalculator("my-project")
    roi_percentage = roi.calculate([{"tokens": 1000, "time_saved": 2}])
"""
from __future__ import annotations

import json
import os
from typing import Optional

class ROICalculator:
    """ROI tracking for multi-agent workflows."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.costs = self._load_costs()
        self.benefits = self._load_benefits()

    def _load_costs(self) -> dict:
        """Load cost parameters."""
        return {
            "agent_cost": 0.03,  # $0.03 per 1k tokens (Codex)
            "human_cost": 50.0   # $50/hour (human)
        }

    def _load_benefits(self) -> dict:
        """Load benefit parameters."""
        return {
            "efficiency_gain": 0.61  # 61% boost (FwdSlash)
        }

    def calculate(self, tasks: list[dict]) -> float:
        """Calculate ROI for a list of tasks."""
        total_cost = sum(task["tokens"] * self.costs["agent_cost"] / 1000 for task in tasks)
        human_time_saved = sum(task["time_saved"] for task in tasks)  # hours
        total_benefit = human_time_saved * self.costs["human_cost"] * self.benefits["efficiency_gain"]
        return (total_benefit - total_cost) / total_cost * 100  # ROI %

class TokenOptimizer:
    """Token cost optimization via caching and model routing."""

    def __init__(self):
        self.cache = {}
        self.models = {
            "codex/gpt-5.5": {"cost_per_1k_tokens": 0.03, "cacheable": True},
            "minimax/abab6.5s-chat": {"cost_per_1k_tokens": 0.001, "cacheable": False},
            "claude/sonnet-4": {"cost_per_1k_tokens": 0.015, "cacheable": True}
        }

    def optimize(self, prompt: str, model: str) -> tuple[str, float]:
        """Optimize token usage via caching."""
        if self.models[model]["cacheable"] and prompt in self.cache:
            return self.cache[prompt], 0.0  # Cached: $0 cost
        self.cache[prompt] = prompt  # Cache miss: store for next time
        return prompt, self.models[model]["cost_per_1k_tokens"] * len(prompt.split()) / 1000

class CostOptimizer:
    """Optimizes model routing based on cost and task tier."""

    def __init__(self):
        self.models = {
            "codex/gpt-5.5": {"cost_per_1k_tokens": 0.03, "tier": 3},
            "minimax/abab6.5s-chat": {"cost_per_1k_tokens": 0.001, "tier": 0},
            "claude/sonnet-4": {"cost_per_1k_tokens": 0.015, "tier": 2}
        }

    def route(self, task: str, budget: float) -> tuple[str, str]:
        """Route task to the most cost-effective model within budget."""
        required_tier = self._get_task_tier(task)
        for model, specs in sorted(self.models.items(), key=lambda x: x[1]["cost_per_1k_tokens"]):
            if specs["tier"] >= required_tier and specs["cost_per_1k_tokens"] <= budget:
                return model.split("/")
        return ("codex", "gpt-5.5")  # Fallback

    def _get_task_tier(self, task: str) -> int:
        """Determine task tier based on keywords."""
        if any(keyword in task.lower() for keyword in ["security", "compliance", "audit"]):
            return 3
        elif any(keyword in task.lower() for keyword in ["refactor", "debug", "optimize"]):
            return 2
        else:
            return 0
