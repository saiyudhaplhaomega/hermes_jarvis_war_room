"""Army Operations API for dashboard-local CLI worker orchestration.

This module is deliberately conservative for v1:
- It writes only dashboard-owned run state/workspaces.
- It never mutates Hermes profiles or profile configs.
- It never uses shell=True.
- Approval is a state transition, not a merge/push/apply operation.
"""
from __future__ import annotations

import difflib
import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from auth.dependencies import get_current_user
from core.config import DASHBOARD_DATA

router = APIRouter(prefix="/army", tags=["army"])

SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
RUN_STATE_FILE = Path(os.environ.get("JARVIS_DASHBOARD_ARMY_STATE", str(DASHBOARD_DATA / "army_runs.json"))).expanduser()
RUNS_DIR = Path(os.environ.get("JARVIS_DASHBOARD_ARMY_RUNS", str(DASHBOARD_DATA / "army_runs"))).expanduser()
DISABLE_EXEC = os.environ.get("JARVIS_DASHBOARD_ARMY_DISABLE_EXEC", "").lower() in {"1", "true", "yes"}
SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|auth[_-]?token|password|secret)\s*[:=]\s*\S+"),
]


class RunRequest(BaseModel):
    worker: str = Field(default="claude", min_length=1, max_length=32)
    task: str = Field(min_length=1, max_length=4000)
    repo: str = Field(default="", max_length=1000)
    dry_run: bool = True

    @field_validator("worker")
    @classmethod
    def safe_worker(cls, value: str) -> str:
        return _safe_id(value, "worker")


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class RunRecord(BaseModel):
    run_id: str
    parent_run_id: str = ""
    worker: str
    task: str
    repo: str = ""
    status: Literal["queued", "running", "completed", "failed", "needs_review", "approved", "rejected"]
    created_at: str
    updated_at: str
    started_at: str = ""
    finished_at: str = ""
    exit_code: int | None = None
    workspace_path: str
    log_path: str
    reject_reason: str = ""
    writes_profile_configs: bool = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_id(value: str, label: str = "identifier") -> str:
    if not value or "/" in value or "\\" in value or ".." in value or not SAFE_ID.match(value):
        raise ValueError(f"{label} must be a safe identifier")
    return value


def _safe_run_id(run_id: str) -> str:
    try:
        return _safe_id(run_id, "run_id")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _read_state() -> dict:
    if not RUN_STATE_FILE.exists():
        return {"version": 1, "runs": []}
    try:
        data = json.loads(RUN_STATE_FILE.read_text())
    except Exception:
        return {"version": 1, "runs": []}
    if not isinstance(data, dict) or not isinstance(data.get("runs"), list):
        return {"version": 1, "runs": []}
    return data


def _write_state(data: dict) -> None:
    RUN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = RUN_STATE_FILE.with_suffix(RUN_STATE_FILE.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(RUN_STATE_FILE)


def _all_runs() -> list[dict]:
    return list(_read_state().get("runs", []))


def _save_run(run: dict) -> None:
    data = _read_state()
    runs = [item for item in data.get("runs", []) if item.get("run_id") != run.get("run_id")]
    runs.append(run)
    runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    data["runs"] = runs
    data["updated_at"] = _now()
    _write_state(data)


def _get_run(run_id: str) -> dict:
    safe = _safe_run_id(run_id)
    for run in _all_runs():
        if run.get("run_id") == safe:
            return run
    raise HTTPException(status_code=404, detail="run not found")


def _run_paths(run_id: str) -> tuple[Path, Path]:
    safe = _safe_run_id(run_id)
    base = RUNS_DIR.resolve()
    workspace = (base / safe / "workspace").resolve()
    log_path = (base / safe / "logs" / "worker.log").resolve()
    if not str(workspace).startswith(str(base)) or not str(log_path).startswith(str(base)):
        raise HTTPException(status_code=400, detail="run path escapes dashboard state")
    return workspace, log_path


def _redact(text: str) -> str:
    out = text
    for pattern in SECRET_PATTERNS:
        out = pattern.sub("[REDACTED]", out)
    return out


def _worker_roster() -> list[dict]:
    claude_path = shutil.which("claude")
    codex_path = shutil.which("codex")
    return [
        {
            "id": "claude",
            "label": "Claude Code",
            "kind": "cli",
            "available": bool(claude_path),
            "path": claude_path or "",
            "notes": "Primary v1 worker on this host." if claude_path else "Install and authenticate Claude Code first.",
        },
        {
            "id": "codex",
            "label": "Codex CLI",
            "kind": "cli",
            "available": bool(codex_path),
            "path": codex_path or "",
            "notes": "Unavailable on this host until `codex` is installed and authenticated.",
        },
        {
            "id": "minimax",
            "label": "MiniMax M3",
            "kind": "provider",
            "available": False,
            "path": "",
            "notes": "Planned adapter; endpoint/auth must be verified before enabling execution.",
        },
    ]


def _worker_available(worker: str) -> bool:
    return any(item["id"] == worker and item["available"] for item in _worker_roster())


def _create_workspace_files(workspace: Path, task: str, output: str) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "prompt.txt").write_text(task)
    (workspace / "final.txt").write_text(output)
    (workspace / "README.md").write_text(
        "# Army Operations Run Workspace\n\n"
        "This directory is dashboard-local output for a worker run. "
        "It is not automatically merged into any Hermes profile or source tree.\n"
    )


def _execute_run(run: dict, dry_run: bool) -> dict:
    workspace, log_path = _run_paths(run["run_id"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    run["status"] = "running"
    run["started_at"] = _now()
    run["updated_at"] = run["started_at"]
    _save_run(run)

    if dry_run or DISABLE_EXEC:
        output = (
            f"DRY RUN: {run['worker']} would execute this task safely.\n\n"
            f"Task:\n{run['task']}\n\n"
            "No profile configs, prompts, .env files, or gateway bindings were modified.\n"
        )
        _create_workspace_files(workspace, run["task"], output)
        log_path.write_text(_redact(output))
        run["exit_code"] = 0
        run["status"] = "needs_review"
    else:
        if run["worker"] != "claude":
            raise HTTPException(status_code=400, detail="worker is not executable in v1")
        if not _worker_available("claude"):
            raise HTTPException(status_code=400, detail="claude worker is unavailable")
        workspace.mkdir(parents=True, exist_ok=True)
        cmd = ["claude", "-p", run["task"], "--tools", "", "--max-turns", "1", "--output-format", "text"]
        proc = subprocess.run(cmd, cwd=str(workspace), capture_output=True, text=True, timeout=180, shell=False)
        output = (proc.stdout or "") + (proc.stderr or "")
        output = _redact(output)
        _create_workspace_files(workspace, run["task"], output)
        log_path.write_text(output)
        run["exit_code"] = int(proc.returncode)
        run["status"] = "needs_review" if proc.returncode == 0 else "failed"

    run["finished_at"] = _now()
    run["updated_at"] = run["finished_at"]
    _save_run(run)
    return run


def _unified_diff_for_workspace(workspace: Path) -> str:
    if not workspace.exists():
        return ""
    parts: list[str] = []
    for file_path in sorted(p for p in workspace.rglob("*") if p.is_file()):
        rel = file_path.relative_to(workspace)
        try:
            new_lines = file_path.read_text(errors="replace").splitlines(keepends=True)
        except Exception:
            continue
        parts.extend(difflib.unified_diff([], new_lines, fromfile=f"base/{rel}", tofile=f"workspace/{rel}"))
    return "".join(parts)


@router.get("/workers")
def get_workers(user: str = Depends(get_current_user)):
    return {"workers": _worker_roster(), "writes_profile_configs": False}


@router.get("/runs")
def list_runs(user: str = Depends(get_current_user)):
    return {"runs": _all_runs(), "writes_profile_configs": False}


@router.post("/runs")
def spawn_run(payload: RunRequest, user: str = Depends(get_current_user)):
    if payload.worker not in {"claude", "codex", "minimax"}:
        raise HTTPException(status_code=400, detail="unknown worker")
    if payload.worker != "claude" and not payload.dry_run:
        raise HTTPException(status_code=400, detail="worker is unavailable for execution in v1")
    if payload.worker == "claude" and not payload.dry_run and not _worker_available("claude"):
        raise HTTPException(status_code=400, detail="claude worker is unavailable")

    run_id = f"run-{uuid.uuid4().hex[:12]}"
    workspace, log_path = _run_paths(run_id)
    now = _now()
    run = RunRecord(
        run_id=run_id,
        worker=payload.worker,
        task=payload.task,
        repo=payload.repo,
        status="queued",
        created_at=now,
        updated_at=now,
        workspace_path=str(workspace),
        log_path=str(log_path),
    ).model_dump()
    _save_run(run)
    run = _execute_run(run, payload.dry_run)
    return {"run": run, "writes_profile_configs": False}


@router.get("/runs/{run_id}")
def get_run(run_id: str, user: str = Depends(get_current_user)):
    return {"run": _get_run(run_id), "writes_profile_configs": False}


@router.get("/runs/{run_id}/logs")
def get_logs(run_id: str, user: str = Depends(get_current_user)):
    run = _get_run(run_id)
    log_path = Path(run.get("log_path", ""))
    logs = log_path.read_text(errors="replace") if log_path.exists() else ""
    return {"run_id": run["run_id"], "logs": _redact(logs), "writes_profile_configs": False}


@router.get("/runs/{run_id}/diff")
def get_diff(run_id: str, user: str = Depends(get_current_user)):
    run = _get_run(run_id)
    workspace = Path(run.get("workspace_path", ""))
    return {"run_id": run["run_id"], "diff": _unified_diff_for_workspace(workspace), "writes_profile_configs": False}


@router.post("/runs/{run_id}/reject")
def reject_run(run_id: str, payload: RejectRequest, user: str = Depends(get_current_user)):
    run = _get_run(run_id)
    run["status"] = "rejected"
    run["reject_reason"] = payload.reason
    run["updated_at"] = _now()
    _save_run(run)
    return {"run": run, "writes_profile_configs": False}


@router.post("/runs/{run_id}/rerun")
def rerun(run_id: str, user: str = Depends(get_current_user)):
    parent = _get_run(run_id)
    feedback = parent.get("reject_reason") or "no prior reject reason recorded"
    now = _now()
    new_id = f"run-{uuid.uuid4().hex[:12]}"
    workspace, log_path = _run_paths(new_id)
    task = f"{parent.get('task', '')}\n\nPrevious reject reason: {feedback}"
    child = RunRecord(
        run_id=new_id,
        parent_run_id=parent["run_id"],
        worker=parent.get("worker", "claude"),
        task=task,
        repo=parent.get("repo", ""),
        status="queued",
        created_at=now,
        updated_at=now,
        workspace_path=str(workspace),
        log_path=str(log_path),
    ).model_dump()
    _save_run(child)
    child = _execute_run(child, True)
    return {"run": child, "writes_profile_configs": False}


@router.post("/runs/{run_id}/approve")
def approve_run(run_id: str, user: str = Depends(get_current_user)):
    run = _get_run(run_id)
    run["status"] = "approved"
    run["updated_at"] = _now()
    _save_run(run)
    return {"run": run, "merged": False, "writes_profile_configs": False}
