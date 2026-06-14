"""Agent Cron Jobs API.

Persists user-defined scheduled jobs in
`~/.hermes/state/dashboard/agent_cron_jobs.json`. Jobs can be:

  - cron (5-field POSIX cron expression)
  - interval (every N seconds)
  - one_shot (run once at a specific ISO timestamp, then auto-disable)

When a job fires, the launcher's scheduler loop (or the SPA's
poll-and-fire worker) invokes the target agent with the given
`prompt` against the dashboard's `/chat` endpoint. The chat route
already exists and uses the full LLM provider chain (HTTP API → CLI
fallback → template).

All endpoints keep `writes_profile_configs: false` — the cron jobs
live in dashboard-local state, never touching real Hermes profiles.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from auth.dependencies import get_current_user
from core.config import DASHBOARD_DATA

router = APIRouter(tags=["agent-cron"])

JOBS_FILE = Path(os.environ.get(
    "JARVIS_DASHBOARD_AGENT_CRON_JOBS",
    str(DASHBOARD_DATA / "agent_cron_jobs.json"),
)).expanduser()

# Very loose 5-field cron validator: m h dom mon dow
# m,h,dom,mon,dow — each either *, number, or comma list of numbers
_CRON_RE = re.compile(
    r"^\s*([\d*/,\-]+)\s+([\d*/,\-]+)\s+([\d*/,\-]+)\s+([\d*/,\-]+)\s+([\d*/,\-]+)\s*$"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_jobs() -> dict:
    return _read_json(JOBS_FILE, {"version": 1, "updated_at": "", "jobs": []})


def _write_jobs(data: dict) -> None:
    data["updated_at"] = _now()
    data["version"] = int(data.get("version", 1)) + 1
    _write_json(JOBS_FILE, data)


def _read_json(path: Path, default: dict) -> dict:
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return default


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _safe_slug(value: str, field_name: str) -> str:
    v = (value or "").strip()
    if not v:
        raise HTTPException(status_code=422, detail=f"{field_name} cannot be empty")
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$", v):
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} must be 1-64 chars, alphanumeric/underscore/dot/hyphen",
        )
    return v


# ─── models ────────────────────────────────────────────────────────

class CronJobBase(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    agent: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=4000, description="What to send to the agent on each run")
    schedule_type: Literal["cron", "interval", "one_shot"]
    # cron
    cron_expression: str = Field(default="", max_length=120, description="5-field POSIX cron, e.g. '*/5 * * * *'")
    # interval
    interval_seconds: int = Field(default=0, ge=0, le=86400 * 30, description="For schedule_type='interval'")
    # one_shot
    run_at: str = Field(default="", max_length=64, description="ISO 8601 UTC timestamp for one_shot jobs")
    # optional
    project: str = Field(default="default", max_length=64)
    enabled: bool = True
    notes: str = Field(default="", max_length=500)

    @field_validator("agent")
    @classmethod
    def safe_agent(cls, value: str) -> str:
        return _safe_slug(value, "agent")

    @field_validator("name")
    @classmethod
    def safe_name(cls, value: str) -> str:
        return _safe_slug(value, "name")

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, value: str, info) -> str:
        # only validate when cron is the chosen type
        if info.data.get("schedule_type") == "cron":
            if not value or not _CRON_RE.match(value):
                raise HTTPException(
                    status_code=422,
                    detail="cron_expression must be 5 space-separated fields (min hour dom month dow), each field can be * or digits or comma-list",
                )
        return value


class CronJobCreate(CronJobBase):
    pass


class CronJobUpdate(BaseModel):
    name: Optional[str] = None
    agent: Optional[str] = None
    prompt: Optional[str] = None
    schedule_type: Optional[Literal["cron", "interval", "one_shot"]] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    run_at: Optional[str] = None
    project: Optional[str] = None
    enabled: Optional[bool] = None
    notes: Optional[str] = None


# ─── endpoints ────────────────────────────────────────────────────

@router.get("/cron/jobs")
def list_jobs(
    agent: Optional[str] = None,
    enabled: Optional[bool] = None,
    user: str = Depends(get_current_user),
):
    """List all cron jobs, with optional agent/enabled filters."""
    data = _read_jobs()
    jobs = data.get("jobs", [])
    if agent:
        jobs = [j for j in jobs if j.get("agent") == agent]
    if enabled is not None:
        jobs = [j for j in jobs if bool(j.get("enabled", True)) == bool(enabled)]
    return {
        "writes_profile_configs": False,
        "version": data.get("version", 1),
        "count": len(jobs),
        "jobs": jobs,
    }


@router.get("/cron/jobs/{job_id}")
def get_job(job_id: str, user: str = Depends(get_current_user)):
    data = _read_jobs()
    for j in data.get("jobs", []):
        if j.get("id") == job_id:
            return j
    raise HTTPException(status_code=404, detail=f"no cron job with id={job_id!r}")


@router.post("/cron/jobs")
def create_job(req: CronJobCreate, user: str = Depends(get_current_user)):
    """Create a new cron job."""
    # Type-specific validation
    if req.schedule_type == "interval" and req.interval_seconds <= 0:
        raise HTTPException(status_code=422, detail="interval_seconds must be > 0 for schedule_type='interval'")
    if req.schedule_type == "one_shot" and not req.run_at:
        raise HTTPException(status_code=422, detail="run_at is required for schedule_type='one_shot'")
    if req.schedule_type == "one_shot" and req.run_at:
        try:
            datetime.fromisoformat(req.run_at.replace("Z", "+00:00"))
        except Exception:
            raise HTTPException(status_code=422, detail="run_at must be ISO 8601")

    data = _read_jobs()
    jobs = data.get("jobs", [])

    # Reject duplicate name
    if any(j.get("name") == req.name for j in jobs):
        raise HTTPException(status_code=422, detail=f"a job with name={req.name!r} already exists")

    new_job = {
        "id": str(uuid.uuid4())[:12],
        **req.model_dump(),
        "created_at": _now(),
        "created_by": user,
        "updated_at": _now(),
        "last_run_at": "",
        "last_run_status": "",
        "last_error": "",
        "run_count": 0,
    }
    jobs.append(new_job)
    data["jobs"] = jobs
    _write_jobs(data)
    return {
        "writes_profile_configs": False,
        "created": new_job["id"],
        "job": new_job,
    }


@router.patch("/cron/jobs/{job_id}")
def update_job(job_id: str, req: CronJobUpdate, user: str = Depends(get_current_user)):
    """Partially update a cron job (any subset of fields)."""
    data = _read_jobs()
    jobs = data.get("jobs", [])
    found = None
    for j in jobs:
        if j.get("id") == job_id:
            found = j
            break
    if found is None:
        raise HTTPException(status_code=404, detail=f"no cron job with id={job_id!r}")
    updates = req.model_dump(exclude_unset=True)
    # Validate agent/name if present
    if "agent" in updates and updates["agent"]:
        updates["agent"] = _safe_slug(updates["agent"], "agent")
    if "name" in updates and updates["name"]:
        updates["name"] = _safe_slug(updates["name"], "name")
    # Validate cron expression
    if updates.get("schedule_type") == "cron" and updates.get("cron_expression"):
        if not _CRON_RE.match(updates["cron_expression"]):
            raise HTTPException(status_code=422, detail="cron_expression is invalid (5 fields: min hour dom month dow)")
    # Validate interval
    if updates.get("schedule_type") == "interval":
        if (updates.get("interval_seconds") or 0) <= 0:
            raise HTTPException(status_code=422, detail="interval_seconds must be > 0")
    found.update(updates)
    found["updated_at"] = _now()
    data["jobs"] = jobs
    _write_jobs(data)
    return {"writes_profile_configs": False, "updated": job_id, "job": found}


@router.delete("/cron/jobs/{job_id}")
def delete_job(job_id: str, user: str = Depends(get_current_user)):
    data = _read_jobs()
    before = len(data.get("jobs", []))
    data["jobs"] = [j for j in data.get("jobs", []) if j.get("id") != job_id]
    if len(data["jobs"]) == before:
        raise HTTPException(status_code=404, detail=f"no cron job with id={job_id!r}")
    _write_jobs(data)
    return {"writes_profile_configs": False, "deleted": job_id, "remaining": len(data["jobs"])}


@router.post("/cron/jobs/{job_id}/run")
async def run_job_now(job_id: str, user: str = Depends(get_current_user)):
    """Manually trigger a job immediately (bypasses its schedule).

    The SPA's scheduler loop is the real consumer: when it sees a job is
    due, it POSTs here, then opens a chat session to actually fire the
    prompt at the agent. We just record the run and return the dispatch
    payload.
    """
    data = _read_jobs()
    jobs = data.get("jobs", [])
    found = None
    for j in jobs:
        if j.get("id") == job_id:
            found = j
            break
    if found is None:
        raise HTTPException(status_code=404, detail=f"no cron job with id={job_id!r}")
    found["last_run_at"] = _now()
    found["last_run_status"] = "dispatched"
    found["run_count"] = int(found.get("run_count", 0)) + 1
    for j in jobs:
        if j.get("id") == job_id:
            j.update(found)
            break
    _write_jobs(data)
    return {
        "writes_profile_configs": False,
        "dispatched": True,
        "agent": found.get("agent"),
        "prompt": found.get("prompt"),
        "job": found,
    }
