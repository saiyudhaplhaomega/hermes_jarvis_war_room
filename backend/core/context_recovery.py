"""
LivingOntology for real-time IT context.

Usage:
    from backend.core.context_recovery import LivingOntology
    ontology = LivingOntology("my-project")
    assets = ontology.query("assets")
"""
from __future__ import annotations

import json
import os
from typing import Optional

class LivingOntology:
    """Real-time enterprise knowledge graph."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.graph = self._load_graph()

    def _load_graph(self) -> dict:
        """Load ontology from ~/.hermes/memory/projects/<project_id>/ontology.json."""
        ontology_path = os.path.expanduser(
            f"~/.hermes/memory/projects/{self.project_id}/ontology.json"
        )
        try:
            with open(ontology_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "assets": {
                    "servers": ["prod-1", "prod-2"],
                    "databases": ["postgres-1"]
                },
                "dependencies": {
                    "prod-1": ["postgres-1"]
                }
            }

    def query(self, entity: str) -> dict:
        """Query the knowledge graph."""
        return self.graph.get(entity, {})

    def update_graph(self, entity: str, data: dict) -> None:
        """Update the knowledge graph."""
        self.graph[entity] = data
        self._save_graph()

    def _save_graph(self) -> None:
        """Save graph to disk."""
        ontology_path = os.path.expanduser(
            f"~/.hermes/memory/projects/{self.project_id}/ontology.json"
        )
        with open(ontology_path, "w") as f:
            json.dump(self.graph, f)
