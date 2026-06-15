"""Worker Adapter Interface: Pluggable adapters for CLI, API, and provider models."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional

log = logging.getLogger("jarvis.adapters")


class WorkerAdapter(ABC):
    """Abstract base class for worker adapters."""

    @abstractmethod
    def execute(self, task: Dict) -> Dict:
        """Execute a task."""
        pass

    @abstractmethod
    def estimate_cost(self, task: Dict) -> float:
        """Estimate cost for a task."""
        pass

    @abstractmethod
    def estimate_latency(self, task: Dict) -> float:
        """Estimate latency for a task (seconds)."""
        pass


class CLIAdapter(WorkerAdapter):
    """Adapter for CLI-based workers."""

    def execute(self, task: Dict) -> Dict:
        """Execute a task via CLI."""
        log.info("Executing CLI task: %s", task.get("command"))
        return {"status": "completed", "output": "CLI task completed"}

    def estimate_cost(self, task: Dict) -> float:
        """Estimate cost for a CLI task."""
        return 0.0  # CLI tasks are free

    def estimate_latency(self, task: Dict) -> float:
        """Estimate latency for a CLI task."""
        return 1.0  # 1 second


class APIAdapter(WorkerAdapter):
    """Adapter for API-based workers."""

    def execute(self, task: Dict) -> Dict:
        """Execute a task via API."""
        log.info("Executing API task: %s", task.get("endpoint"))
        return {"status": "completed", "output": "API task completed"}

    def estimate_cost(self, task: Dict) -> float:
        """Estimate cost for an API task."""
        return 0.01  # $0.01 per task

    def estimate_latency(self, task: Dict) -> float:
        """Estimate latency for an API task."""
        return 2.0  # 2 seconds


class ProviderAdapter(WorkerAdapter):
    """Adapter for provider-based workers (e.g., Codex, Claude)."""

    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model

    def execute(self, task: Dict) -> Dict:
        """Execute a task via provider."""
        log.info("Executing %s/%s task: %s", self.provider, self.model, task.get("prompt"))
        return {"status": "completed", "output": "Provider task completed"}

    def estimate_cost(self, task: Dict) -> float:
        """Estimate cost for a provider task."""
        # Simplified cost model
        cost_per_token = 0.0001  # $0.0001 per token
        tokens = len(task.get("prompt", "")) / 4  # Rough token estimate
        return cost_per_token * tokens

    def estimate_latency(self, task: Dict) -> float:
        """Estimate latency for a provider task."""
        return 5.0  # 5 seconds


# Adapter registry
ADAPTERS = {
    "cli": CLIAdapter(),
    "api": APIAdapter(),
    "codex/gpt-5.5": ProviderAdapter("codex", "gpt-5.5"),
    "claude/sonnet": ProviderAdapter("claude", "sonnet"),
}


def get_adapter(adapter_name: str) -> WorkerAdapter:
    """Get an adapter by name."""
    adapter = ADAPTERS.get(adapter_name)
    if not adapter:
        raise ValueError(f"Adapter not found: {adapter_name}")
    return adapter
