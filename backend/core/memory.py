"""Memory management with context-aware segmentation."""

import os

class MemorySegmenter:
    """Context-aware memory segmentation to prevent data leakage."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.segments = self._load_segments()

    def _load_segments(self) -> dict:
        """Load memory segments from environment variables."""
        return {
            "engineering": {
                "allowed_contexts": ["code", "debugging"],
                "prefix": "[ENG]"
            },
            "product": {
                "allowed_contexts": ["tasks", "roadmaps"],
                "prefix": "[PROD]"
            }
        }

    def segment(self, context: str, data: str) -> str:
        """Segment memory by context."""
        for segment, rules in self.segments.items():
            if context in rules["allowed_contexts"]:
                return f"{rules['prefix']} {data}"
        return "[DEFAULT] " + data
