"""Transactional write service for agent lifecycle operations."""

import json
import logging
import os
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException

from core.config import DASHBOARD_DATA

log = logging.getLogger("jarvis.transactional")

# Lock for cross-process file operations
_transaction_lock = threading.Lock()

class TransactionalWriteService:
    """Service for atomic multi-file writes with rollback on failure."""

    def __init__(self, base_dir: Path = DASHBOARD_DATA):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def atomic_write(self, files: List[Tuple[Path, Dict]]):
        """Context manager for atomic multi-file writes.

        Args:
            files: List of (file_path, data_dict) tuples.
        """
        tmp_files = []
        try:
            # Write to temporary files
            for file_path, data in files:
                tmp_path = file_path.with_suffix(f".tmp.{uuid.uuid4().hex[:8]}")
                tmp_path.write_text(json.dumps(data, indent=2))
                tmp_files.append(tmp_path)

            # Acquire lock and replace original files
            with _transaction_lock:
                for (file_path, _), tmp_path in zip(files, tmp_files):
                    tmp_path.replace(file_path)
            yield
        except Exception as e:
            # Rollback on failure
            for tmp_path in tmp_files:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
            log.error("Transactional write failed: %s", e)
            raise HTTPException(status_code=500, detail="Transactional write failed") from e
        finally:
            # Clean up temporary files
            for tmp_path in tmp_files:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def propose_agent(self, agent_data: Dict) -> Path:
        """Propose a new agent with atomic write."""
        agent_id = agent_data.get("id", f"agent_{uuid.uuid4().hex[:8]}")
        proposal_path = self.base_dir / "proposals" / f"{agent_id}.json"
        proposal_path.parent.mkdir(parents=True, exist_ok=True)

        with self.atomic_write([(proposal_path, agent_data)]):
            log.info("Proposed agent: %s", agent_id)
            return proposal_path

    def assign_agent(self, agent_id: str, assignment_data: Dict) -> Path:
        """Assign an agent with atomic write."""
        assignment_path = self.base_dir / "assignments" / f"{agent_id}.json"
        assignment_path.parent.mkdir(parents=True, exist_ok=True)

        with self.atomic_write([(assignment_path, assignment_data)]):
            log.info("Assigned agent: %s", agent_id)
            return assignment_path

    def retire_agent(self, agent_id: str, tombstone_data: Dict) -> Path:
        """Retire an agent with atomic write."""
        tombstone_path = self.base_dir / "tombstones" / f"{agent_id}.json"
        tombstone_path.parent.mkdir(parents=True, exist_ok=True)

        with self.atomic_write([(tombstone_path, tombstone_data)]):
            log.info("Retired agent: %s", agent_id)
            return tombstone_path


# Singleton instance
transactional_service = TransactionalWriteService()
