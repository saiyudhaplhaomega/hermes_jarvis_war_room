"""Agent Skill Marketplace: Curated feed of GitHub repos."""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.config import DASHBOARD_DATA
from auth.dependencies import get_current_user

log = logging.getLogger("jarvis.marketplace")
router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class SkillRepo(BaseModel):
    """A GitHub repository with skills."""
    repo_id: str
    name: str
    owner: str
    description: str
    stars: int
    trust_tier: str  # bronze, silver, gold
    last_updated: str
    skills: List[str] = Field(default_factory=list)


class MarketplaceService:
    """Service for skill discovery and import."""

    def __init__(self, base_dir: Path = DASHBOARD_DATA):
        self.base_dir = base_dir
        self.feed_path = base_dir / "marketplace_feed.json"
        self._load_feed()

    def _load_feed(self) -> None:
        """Load curated feed from disk."""
        if not self.feed_path.exists():
            self.feed = []
            return
        try:
            self.feed = [SkillRepo(**item) for item in json.loads(self.feed_path.read_text())]
        except Exception as e:
            log.error("Failed to load marketplace feed: %s", e)
            self.feed = []

    def _save_feed(self) -> None:
        """Save curated feed to disk."""
        self.feed_path.write_text(json.dumps([repo.dict() for repo in self.feed], indent=2))

    def add_repo(self, repo: SkillRepo) -> SkillRepo:
        """Add a repository to the curated feed."""
        self.feed.append(repo)
        self._save_feed()
        return repo

    def import_skill(self, repo_id: str, skill_name: str) -> Dict:
        """Import a skill from a repository."""
        repo = next((r for r in self.feed if r.repo_id == repo_id), None)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        if skill_name not in repo.skills:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        # Simulate import
        log.info("Importing skill %s from repo %s", skill_name, repo_id)
        return {
            "status": "imported",
            "skill": skill_name,
            "repo": repo_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Singleton instance
marketplace_service = MarketplaceService()


@router.get("/feed")
def get_feed(user: str = Depends(get_current_user)) -> List[SkillRepo]:
    """Get the curated skill repository feed."""
    return marketplace_service.feed


@router.post("/import")
def import_skill(
    repo_id: str,
    skill_name: str,
    user: str = Depends(get_current_user),
) -> Dict:
    """Import a skill from a repository."""
    return marketplace_service.import_skill(repo_id, skill_name)
