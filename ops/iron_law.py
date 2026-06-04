"""IRON LAW fresh-evidence gate.

Confidence is not evidence; re-run before release.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable


class FreshEvidenceGate:
    """Compare evidence timestamp to source/config mtimes."""

    def __init__(self, evidence_file: Path) -> None:
        self.evidence_file = Path(evidence_file)

    def is_fresh(self, *, roots: Iterable[Path]) -> bool:
        if not self.evidence_file.exists():
            return False
        try:
            record = json.loads(self.evidence_file.read_text())
            ts = float(record.get("timestamp", 0))
        except (json.JSONDecodeError, ValueError):
            return False
        if ts <= 0:
            return False
        for root in roots:
            root_path = Path(root)
            if not root_path.exists():
                continue
            if root_path.is_file():
                if root_path.stat().st_mtime > ts:
                    return False
                continue
            for path in root_path.rglob("*"):
                if not path.is_file():
                    continue
                if path == self.evidence_file:
                    continue
                if path.stat().st_mtime > ts:
                    return False
        return True
