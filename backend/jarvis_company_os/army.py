"""Agent army orchestration."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
import json

from backend.worker.tasks import execute_run_task
from celery.result import AsyncResult

log = logging.getLogger("jarvis.army")
router = APIRouter(prefix="/army", tags=["army"])


def _execute_run(run_id: str, run_data: Dict) -> Dict:
    """Execute a run (simulated)."""
    log.info("Executing run %s", run_id)
    return {"status": "completed", "output": "Run completed successfully"}


def create_run(run_data: Dict) -> Dict:
    """Create and queue a run."""
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    task = execute_run_task.delay(run_id, run_data)
    return {"status": "queued", "task_id": task.id}


def get_run(task_id: str) -> Dict:
    """Get run status."""
    task = AsyncResult(task_id)
    return {"status": task.status, "result": task.result if task.ready() else None}

import threading

# Lock for state read-modify-write
_state_lock = threading.Lock()


def _read_state() -> Dict:
    """Read state with lock."""
    with _state_lock:
        state_path = DASHBOARD_DATA / "army_state.json"
        if not state_path.exists():
            return {}
        try:
            return json.loads(state_path.read_text())
        except Exception as e:
            log.error("Failed to read state: %s", e)
            return {}


def _write_state(state: Dict) -> None:
    """Write state with lock."""
    with _state_lock:
        state_path = DASHBOARD_DATA / "army_state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = state_path.with_suffix(state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(state, indent=2))
        tmp.replace(state_path)

class RunMetadata(BaseModel):
    """Metadata for run execution."""
    run_id: str
    attempt: int = 1
    max_attempts: int = 3
    retry_after: Optional[str] = None
    failure_reason: Optional[str] = None


def create_run(run_data: Dict) -> Dict:
    """Create and queue a run with retry metadata."""
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    metadata = RunMetadata(run_id=run_id)
    run_data["metadata"] = metadata.dict()
    task = execute_run_task.delay(run_id, run_data)
    return {"status": "queued", "task_id": task.id}


@app.task(bind=True, max_retries=3)
def execute_run_task(self, run_id: str, run_data: Dict) -> Dict:
    """Execute a run with retry metadata."""
    try:
        metadata = RunMetadata(**run_data.get("metadata", {}))
        metadata.attempt = self.request.retries + 1
        run_data["metadata"] = metadata.dict()
        
        # Simulate run execution
        log.info("Executing run %s (attempt %d)", run_id, metadata.attempt)
        return {"status": "completed", "result": {"output": "Run completed successfully"}}
    except Exception as e:
        metadata.failure_reason = str(e)
        metadata.retry_after = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
        run_data["metadata"] = metadata.dict()
        log.error("Run %s failed (attempt %d): %s", run_id, metadata.attempt, e)
        self.retry(exc=e, countdown=60)

# Valid run status transitions
VALID_RUN_TRANSITIONS = {
    "queued": ["running"],
    "running": ["needs_review", "failed", "completed"],
    "needs_review": ["running", "failed", "completed"],
    "failed": [],
    "completed": [],
}


def _validate_run_transition(current: str, next_status: str) -> None:
    """Validate run status transition."""
    if next_status not in VALID_RUN_TRANSITIONS.get(current, []):
        raise ValueError(f"Invalid transition: {current} → {next_status}")


@app.task(bind=True, max_retries=3)
def execute_run_task(self, run_id: str, run_data: Dict) -> Dict:
    """Execute a run with status validation."""
    try:
        metadata = RunMetadata(**run_data.get("metadata", {}))
        metadata.attempt = self.request.retries + 1
        
        # Validate transition: queued → running
        _validate_run_transition("queued", "running")
        run_data["status"] = "running"
        run_data["metadata"] = metadata.dict()
        
        # Simulate run execution
        log.info("Executing run %s (attempt %d)", run_id, metadata.attempt)
        
        # Validate transition: running → completed
        _validate_run_transition("running", "completed")
        run_data["status"] = "completed"
        return {"status": "completed", "result": {"output": "Run completed successfully"}}
    except Exception as e:
        metadata.failure_reason = str(e)
        metadata.retry_after = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
        run_data["metadata"] = metadata.dict()
        
        # Validate transition: running → failed
        _validate_run_transition("running", "failed")
        run_data["status"] = "failed"
        log.error("Run %s failed (attempt %d): %s", run_id, metadata.attempt, e)
        self.retry(exc=e, countdown=60)
