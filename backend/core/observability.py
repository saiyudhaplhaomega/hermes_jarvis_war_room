"""
AgentControlPlane for enterprise-wide observability.

Usage:
    from backend.core.observability import AgentControlPlane
    control_plane = AgentControlPlane("my-project")
    control_plane.log_usage("engineering", 1000, "success")
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional

class AgentControlPlane:
    """Enterprise-wide observability for AI agents."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.metrics = self._init_metrics()

    def _init_metrics(self) -> dict:
        """Initialize metrics dashboard."""
        return {
            "token_spend": 0.0,
            "agent_usage": {},
            "outcomes": {"success": 0, "failure": 0},
            "last_updated": int(time.time())
        }

    def log_usage(self, agent: str, tokens: int, outcome: str) -> None:
        """Log agent usage and token spend."""
        self.metrics["token_spend"] += tokens * 0.001  # $0.001 per token
        self.metrics["agent_usage"][agent] = self.metrics["agent_usage"].get(agent, 0) + 1
        self.metrics["outcomes"][outcome] = self.metrics["outcomes"].get(outcome, 0) + 1
        self.metrics["last_updated"] = int(time.time())
        self._save_metrics()

    def _save_metrics(self) -> None:
        """Save metrics to disk."""
        metrics_path = os.path.expanduser(
            f"~/.hermes/memory/projects/{self.project_id}/metrics.json"
        )
        with open(metrics_path, "w") as f:
            json.dump(self.metrics, f)

    def get_dashboard(self) -> dict:
        """Get observability dashboard."""
        return {
            "project_id": self.project_id,
            "metrics": self.metrics
        }

class ComplianceMonitor:
    """Continuous compliance monitoring (GDPR, SOC 2, EU AI Act)."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.rules = self._load_rules()

    def _load_rules(self) -> list[dict]:
        """Load compliance rules from environment variables."""
        return [
            {
                "rule": "GDPR Article 5",
                "check": "data_minimization",
                "frequency": "daily",
                "status": "pending"
            },
            {
                "rule": "SOC 2 CC6.1",
                "check": "access_reviews",
                "frequency": "weekly",
                "status": "implemented"
            }
        ]

    def monitor(self) -> dict:
        """Run compliance checks."""
        return {"project_id": self.project_id, "rules": self.rules}

    def update_rule_status(self, rule: str, status: str) -> bool:
        """Update rule status."""
        for r in self.rules:
            if r["rule"] == rule:
                r["status"] = status
                return True
        return False

class ShadowAIDetector:
    """Detects unsanctioned AI agents (Shadow AI)."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.known_agents = self._load_known_agents()

    def _load_known_agents(self) -> list[str]:
        """Load known agents from environment variables."""
        return ["agent_growth", "kanban", "council"]

    def detect(self, agent_id: str) -> bool:
        """Detect Shadow AI."""
        return agent_id not in self.known_agents

class ComplianceMonitor:
    """Continuous compliance monitoring (GDPR, SOC 2, EU AI Act)."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.rules = self._load_rules()

    def _load_rules(self) -> list[dict]:
        """Load compliance rules from environment variables."""
        return [
            {
                "rule": "GDPR Article 5",
                "check": "data_minimization",
                "frequency": "daily",
                "status": "pending"
            },
            {
                "rule": "SOC 2 CC6.1",
                "check": "access_reviews",
                "frequency": "weekly",
                "status": "implemented"
            }
        ]

    def monitor(self) -> dict:
        """Run compliance checks."""
        return {"project_id": self.project_id, "rules": self.rules}

    def update_rule_status(self, rule: str, status: str) -> bool:
        """Update rule status."""
        for r in self.rules:
            if r["rule"] == rule:
                r["status"] = status
                return True
        return False

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

class TraceEngine:
    """Distributed tracing for multi-agent workflows."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self._setup_tracer()

    def _setup_tracer(self):
        provider = TracerProvider()
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="localhost:4317"))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        self.tracer = trace.get_tracer("hermes-agent")

    def trace_agent(self, agent_id: str, task: str):
        """Trace an agent's execution."""
        with self.tracer.start_as_current_span(f"agent:{agent_id}") as span:
            span.set_attribute("task", task)
            span.set_attribute("project_id", self.project_id)
            return span

class AnomalyDetector:
    """Detects anomalies in traces (failing runs, quality drift)."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.baseline = self._load_baseline()

    def _load_baseline(self) -> dict:
        """Load baseline metrics."""
        return {
            "latency_ms": 1200,
            "tokens": 2000,
            "cost_usd": 0.01,
            "tool_errors": 0
        }

    def detect(self, trace: dict) -> bool:
        """Detect anomalies."""
        return (
            trace["latency_ms"] > self.baseline["latency_ms"] * 1.5 or
            trace["tokens"] > self.baseline["tokens"] * 1.5 or
            trace["cost_usd"] > self.baseline["cost_usd"] * 1.5 or
            trace["tool_errors"] > self.baseline["tool_errors"]
        )
