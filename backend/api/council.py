"""Council of Departments API (D-2026-06-09, Phase 4 sub-task 4.1).

Dashboard-side REST surface for the council runner at
`backend/core/council_departments.py`. The actual vote logic lives
in core/ so it can be unit-tested without spinning up FastAPI.

Endpoints:
  POST /council/ask              — run a department vote; persist + return the decision
  GET  /council/departments      — list available departments + member counts
  GET  /council/decisions        — list recent decisions (replay)
  GET  /council/decisions/{id}   — fetch a single decision by id

All responses carry `writes_profile_configs: false` — the load-bearing
invariant. The replay store is a single JSON file at
`JARVIS_DASHBOARD_COUNCIL_DECISIONS` (env-overridable, defaults to
`<dashboard_state>/council_decisions.json`). Atomic `tmp.replace`
write, same pattern as `agent_growth.py:194-198` and
`discord_gateway.py:138-162`.

**Phase 5 hardening:** a module-level `_state_lock` (threading.Lock)
guards the read-modify-write of the council decision store via
`_mutate_state(fn)`. Same pattern as discord_gateway — process-local,
single-worker production.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth.dependencies import get_current_user
from core.config import DASHBOARD_DATA
from core.council_departments import (
    CouncilDecision,
    DEFAULT_CHAIRMAN,
    DEFAULT_MEMBER_MODEL,
    CouncilError,
    EmptyDepartment,
    UnknownDepartment,
    UnknownMemberModel,
    UnsafeQuestion,
    list_departments,
    members_of,
    run_department_vote,
)

log = logging.getLogger("jarvis.council_api")
router = APIRouter(prefix="/council", tags=["council"])


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
STATE_FILE = Path(os.environ.get(
    "JARVIS_DASHBOARD_COUNCIL_DECISIONS",
    str(DASHBOARD_DATA / "council_decisions.json"),
)).expanduser()

SAFE_SLUG = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
WRITES_PROFILE_CONFIGS = False

# D-2026-06-09 (Phase 5): module-level state lock for the council
# decision store. Same read-modify-write guard pattern as
# `discord_gateway._state_lock`. Process-local; single-worker only.
_state_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_state() -> dict:
    if not STATE_FILE.exists():
        return {"version": 1, "updated_at": "", "decisions": []}
    try:
        data = json.loads(STATE_FILE.read_text())
    except Exception:
        return {"version": 1, "updated_at": "", "decisions": []}
    if not isinstance(data, dict):
        return {"version": 1, "updated_at": "", "decisions": []}
    decisions = data.get("decisions")
    if not isinstance(decisions, list):
        decisions = []
    return {
        "version": data.get("version", 1),
        "updated_at": data.get("updated_at", ""),
        "decisions": decisions,
    }


def _write_state(state: dict) -> None:
    """Atomic write — same `tmp.replace` pattern as `agent_growth.py:194-198`.

    D-2026-06-09 (Phase 5): callers MUST hold `_state_lock` when calling
    this directly. The public mutation path is `_mutate_state(fn)`.
    """
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(STATE_FILE.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    tmp.replace(STATE_FILE)


def _mutate_state(fn: Callable[[dict], None]) -> dict:
    """Read, mutate, write under a single lock. Returns the new state.

    D-2026-06-09 (Phase 5): the only sanctioned path for council
    state mutations. Mirrors `discord_gateway._mutate_state`.
    """
    with _state_lock:
        state = _read_state()
        fn(state)
        _write_state(state)
        return state


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    department: str = Field(..., min_length=1, max_length=64)
    question: str = Field(..., min_length=4, max_length=2000)
    chairman_provider: Optional[str] = Field(default=None, max_length=32)
    chairman_model: Optional[str] = Field(default=None, max_length=64)
    member_provider: Optional[str] = Field(default=None, max_length=32)
    member_model: Optional[str] = Field(default=None, max_length=64)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/departments")
def get_departments(user: str = Depends(get_current_user)):
    """List the available departments and the members in each."""
    departments = list_departments()
    out = []
    for dept in departments:
        try:
            members = members_of(dept)
        except Exception:
            members = []
        out.append({"department": dept, "member_count": len(members), "members": members})
    return {
        "departments": out,
        "writes_profile_configs": WRITES_PROFILE_CONFIGS,
    }


@router.post("/ask")
def ask_council(req: AskRequest, user: str = Depends(get_current_user)):
    """Run a 3-stage department vote and persist the decision.

    Rejects unknown departments with 404, unsafe questions with 422,
    and unknown model pairs with 422. The chairman and member model
    pairs are optional in the request body — defaults to
    `DEFAULT_CHAIRMAN = ("codex", "gpt-5.5")` and the same for
    members.
    """
    if not SAFE_SLUG.match(req.department):
        raise HTTPException(status_code=422, detail="department name is unsafe")
    # Resolve chairman / member model pairs, falling back to defaults.
    chairman = (
        req.chairman_provider or DEFAULT_CHAIRMAN[0],
        req.chairman_model or DEFAULT_CHAIRMAN[1],
    )
    member = (
        req.member_provider or DEFAULT_MEMBER_MODEL[0],
        req.member_model or DEFAULT_MEMBER_MODEL[1],
    )

    try:
        decision = run_department_vote(
            question=req.question,
            department=req.department,
            chairman=chairman,
            member_model=member,
        )
    except UnknownDepartment as e:
        raise HTTPException(status_code=404, detail=str(e))
    except EmptyDepartment as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnsafeQuestion as e:
        raise HTTPException(status_code=422, detail=str(e))
    except UnknownMemberModel as e:
        raise HTTPException(status_code=422, detail=str(e))
    except CouncilError as e:
        raise HTTPException(status_code=500, detail=f"council error: {e}")

    # Persist for replay (D-2026-06-09 Phase 5: under state lock).
    def _persist(state: dict) -> None:
        state["decisions"].append(decision.to_dict())
        # Bound the replay file size: keep the last 200 decisions.
        if len(state["decisions"]) > 200:
            state["decisions"] = state["decisions"][-200:]
        state["updated_at"] = _now()

    _mutate_state(_persist)

    # D-2026-06-09 (Phase 5, observability): log a single info line
    # after durable persistence. No question text, no synthesis —
    # those go in the decision itself for replay.
    log.info(
        "council.ask decision_id=%s department=%s members=%d confidence=%s "
        "stage3_len=%d question_len=%d",
        decision.decision_id, decision.department, len(decision.members),
        decision.confidence, len(decision.stage3_synthesis or ""),
        len(req.question),
    )

    return {
        "decision": decision.to_dict(),
        "writes_profile_configs": WRITES_PROFILE_CONFIGS,
    }


@router.get("/decisions")
def list_decisions(
    limit: int = Query(50, ge=1, le=200),
    department: Optional[str] = Query(None, max_length=64),
    user: str = Depends(get_current_user),
):
    state = _read_state()
    decisions = state.get("decisions", [])
    if department:
        decisions = [d for d in decisions if d.get("department") == department]
    # Newest first.
    decisions = list(reversed(decisions))[:limit]
    return {
        "decisions": decisions,
        "total": len(state.get("decisions", [])),
        "writes_profile_configs": WRITES_PROFILE_CONFIGS,
    }


@router.get("/decisions/{decision_id}")
def get_decision(decision_id: str, user: str = Depends(get_current_user)):
    if not SAFE_SLUG.match(decision_id):
        raise HTTPException(status_code=422, detail="decision_id is unsafe")
    state = _read_state()
    for d in state.get("decisions", []):
        if d.get("decision_id") == decision_id:
            return {"decision": d, "writes_profile_configs": WRITES_PROFILE_CONFIGS}
    raise HTTPException(status_code=404, detail="decision not found")
