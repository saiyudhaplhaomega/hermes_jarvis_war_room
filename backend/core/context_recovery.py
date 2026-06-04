"""Context recovery: welcome-back summary from real project artifacts.

Never fabricates. If a section has no data, it reports zero, not guessed data.
"""
from __future__ import annotations

import os
import time
from pathlib import Path


class ContextRecovery:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def _indexed(self, subdir: str, suffixes: tuple[str, ...] = (".md",)) -> int:
        path = self.repo_root / subdir
        if not path.exists():
            return 0
        return sum(1 for p in path.rglob("*") if p.is_file() and p.suffix.lower() in suffixes)

    def _recent_files(self, subdir: str, limit: int = 5) -> list[dict]:
        path = self.repo_root / subdir
        if not path.exists():
            return []
        candidates = [p for p in path.rglob("*") if p.is_file()]
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return [
            {
                "path": str(p.relative_to(self.repo_root)),
                "mtime": p.stat().st_mtime,
            }
            for p in candidates[:limit]
        ]

    def summarize(self) -> dict:
        return {
            "files_indexed": self._indexed("docs"),
            "decisions_indexed": self._indexed("decisions"),
            "specs_indexed": self._indexed("docs/security-hardening-batch-a"),
        }

    def welcome_back(self) -> dict:
        recent_docs = self._recent_files("docs")
        recent_decisions = self._recent_files("decisions")
        return {
            "files_indexed": self.summarize()["files_indexed"],
            "decisions_indexed": self.summarize()["decisions_indexed"],
            "specs_indexed": self.summarize()["specs_indexed"],
            "recent_files": recent_docs + recent_decisions,
            "now": time.time(),
        }
