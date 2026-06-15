
class CostOptimizer:
    """Marketplace/auction pattern for cost-aware model routing."""

    def __init__(self):
        self.models = {
            "codex/gpt-5.5": {"cost_per_1k_tokens": 0.03, "tier": 3, "latency": 0.5},
            "minimax/abab6.5s-chat": {"cost_per_1k_tokens": 0.001, "tier": 0, "latency": 0.1},
            "claude/sonnet-4": {"cost_per_1k_tokens": 0.015, "tier": 2, "latency": 0.3}
        }

    def route(self, task: str, budget: float) -> tuple[str, str]:
        """Select cheapest model that meets tier/budget requirements."""
        required_tier = self._get_task_tier(task)
        for model, specs in sorted(self.models.items(), key=lambda x: x[1]["cost_per_1k_tokens"]):
            if (specs["tier"] >= required_tier and 
                specs["cost_per_1k_tokens"] <= budget):
                return model.split("/")
        return ("codex", "gpt-5.5")  # Fallback

    def _get_task_tier(self, task: str) -> int:
        """Map task to tier (0=cheapest, 3=most expensive)."""
        if "refactor" in task.lower() or "debug" in task.lower():
            return 3
        elif "research" in task.lower() or "summarize" in task.lower():
            return 1
        else:
            return 0
