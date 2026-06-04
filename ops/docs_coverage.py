"""Diataxis docs coverage gate.

Required categories: tutorial, how-to, reference, explanation.
"""
from __future__ import annotations

import re
from pathlib import Path


CATEGORIES = ("tutorial", "how-to", "reference", "explanation")

_FILENAME_PATTERNS = {
    "tutorial": re.compile(r"^TUTORIAL\.md$", re.IGNORECASE),
    "how-to": re.compile(r"^HOWTO\.md$|^HOW-TO\.md$|^HOWTO_.*\.md$", re.IGNORECASE),
    "reference": re.compile(r"^REFERENCE\.md$", re.IGNORECASE),
    "explanation": re.compile(r"^EXPLANATION\.md$|.*-EXPLANATION\.md$", re.IGNORECASE),
}


class DiataxisGate:
    def __init__(self, docs_root: Path) -> None:
        self.docs_root = Path(docs_root)

    def _existing(self) -> set[str]:
        found: set[str] = set()
        if not self.docs_root.exists():
            return found
        for path in self.docs_root.iterdir():
            if not path.is_file():
                continue
            for category, pattern in _FILENAME_PATTERNS.items():
                if pattern.match(path.name):
                    found.add(category)
                    break
        return found

    def missing_categories(self) -> list[str]:
        found = self._existing()
        return [c for c in CATEGORIES if c not in found]
