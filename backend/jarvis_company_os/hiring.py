"""jarvis_company_os.hiring — Spec 02 §3 Hiring Loop (board-approved only).

HIRE_REQUEST → rate+headcount+budget check → hires(pending) + issues(type=hire)
  → board inbox (api/inbox) → POST /hires/{id}/approve → inactive agent + edges
  → POST /hires/{id}/reject → close. NO autonomous spawn (locked default).
"""
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("jarvis_company_os.hiring")

KANBAN_DB_PATH = Path("/home/ubuntu/.hermes/kanban.db")


def _db() -> sqlite3.Connection:
    c = sqlite3.connect(str(KANBAN_DB_PATH), timeout=5.0)
    c.row_factory = sqlite3.Row
    return c


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class HireRefused(Exception):
    """Raised when a hire is refused by guardrails. Carries a human reason."""


# ── Guardrail 1: hire rate (per spec 02 §3.2 Boss gap fix) ──────
HIRE_RATE_CAP = 3
HIRE_RATE_WINDOW_HOURS = 24


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_reset(reset_at: Optional[str]) -> Optional[datetime]:
    if not reset_at:
        return None
    try:
        # accept "Z" suffix
        if reset_at.endswith("Z"):
            return datetime.fromisoformat(reset_at[:-1]).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(reset_at)
    except Exception:
        return None


def _check_hire_rate(requested_by: str) -> None:
    """Per-agent hire rate cap. Reads agent.hire_rate_json.count + window.

    Default: max HIRE_RATE_CAP hires per agent per HIRE_RATE_WINDOW_HOURS hours.
    If reset_at is past, treat count as 0 (auto-expire).
    """
    conn = _db()
    try:
        row = conn.execute(
            "SELECT hire_rate_json FROM agents WHERE id = ?", (requested_by,),
        ).fetchone()
        if not row or not row["hire_rate_json"]:
            return
        rate = json.loads(row["hire_rate_json"])
        # Auto-expire: if reset_at is in the past, count is effectively 0
        reset_at = _parse_reset(rate.get("reset_at"))
        if reset_at and reset_at <= datetime.now(timezone.utc):
            return
        if rate.get("count", 0) >= HIRE_RATE_CAP:
            raise HireRefused(
                f"agent {requested_by!r} at hire rate cap "
                f"({rate.get('count')}/{HIRE_RATE_CAP} per {rate.get('window','24h')})"
            )
    finally:
        conn.close()


def _bump_hire_rate(requested_by: str) -> None:
    """Increment the agent's hire_rate counter. Sets reset_at on first bump;
    auto-resets count to 0 if window has expired."""
    conn = _db()
    try:
        row = conn.execute(
            "SELECT hire_rate_json FROM agents WHERE id = ?", (requested_by,),
        ).fetchone()
        rate = {"count": 0, "window": f"{HIRE_RATE_WINDOW_HOURS}h", "reset_at": None}
        if row and row["hire_rate_json"]:
            try:
                rate = json.loads(row["hire_rate_json"])
            except Exception:
                pass
        # Auto-reset if window expired
        reset_at = _parse_reset(rate.get("reset_at"))
        now = datetime.now(timezone.utc)
        if reset_at and reset_at <= now:
            rate["count"] = 0
        # Set/refresh reset_at on bump
        new_reset = (now.timestamp() + HIRE_RATE_WINDOW_HOURS * 3600)
        rate["reset_at"] = __import__("datetime").datetime.fromtimestamp(
            new_reset, tz=timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        rate["count"] = rate.get("count", 0) + 1
        conn.execute(
            "UPDATE agents SET hire_rate_json = ? WHERE id = ?",
            (json.dumps(rate), requested_by),
        )
        conn.commit()
    finally:
        conn.close()


# ── Guardrail 2: company headcount cap (spec 02 §3.2) ──────────
def _check_headcount(company_id: str) -> int:
    conn = _db()
    try:
        cap_row = conn.execute(
            "SELECT max_headcount FROM companies WHERE id = ?", (company_id,),
        ).fetchone()
        cap = cap_row["max_headcount"] if cap_row and cap_row["max_headcount"] else 50
        cur_row = conn.execute(
            "SELECT COUNT(*) AS c FROM agents WHERE company_id = ? AND status != 'inactive'",
            (company_id,),
        ).fetchone()
        cur = cur_row["c"]
        if cur >= cap:
            raise HireRefused(
                f"company {company_id!r} at headcount cap ({cur}/{cap})"
            )
        return cap - cur  # remaining
    finally:
        conn.close()


# ── Guardrail 3: budget cap (spec 03 §3.2) ─────────────────────
def _check_budget(company_id: str, est_monthly_budget: float) -> None:
    if est_monthly_budget is None:
        return  # budget unspecified — skip check
    conn = _db()
    try:
        row = conn.execute(
            """SELECT b.tokens_limit, b.usd_limit, b.usd_used, b.tokens_used
               FROM budgets b
               WHERE b.scope = 'company' AND b.scope_id = ?""",
            (company_id,),
        ).fetchone()
        if not row or row["usd_limit"] is None:
            return  # no company budget row → skip
        if (row["usd_used"] or 0) + est_monthly_budget > row["usd_limit"]:
            raise HireRefused(
                f"hire ${est_monthly_budget}/mo would exceed company budget "
                f"({row['usd_used']}/{row['usd_limit']} USD used)"
            )
    finally:
        conn.close()


# ── Public: submit a hire ──────────────────────────────────────
def submit_hire(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate → run all 3 guardrails → INSERT hires(pending) + issues(type=hire)."""
    required = ("role", "team_id", "justification", "reports_to")
    missing = [k for k in required if not payload.get(k)]
    if missing:
        raise HireRefused(f"missing required: {missing}")

    company_id = payload.get("company_id", "jarvis-war-room")
    requested_by = payload.get("requested_by")
    if not requested_by:
        raise HireRefused("requested_by required")

    # Guardrail 1: rate
    _check_hire_rate(requested_by)
    # Guardrail 2: headcount
    _check_headcount(company_id)
    # Guardrail 3: budget
    _check_budget(company_id, payload.get("est_monthly_budget"))

    hid = payload.get("id") or f"hire-{uuid.uuid4().hex[:8]}"
    iid = f"iss-hire-{hid}"

    conn = _db()
    try:
        conn.execute(
            """INSERT INTO hires
               (id, company_id, requested_by, role, team_id, skills_json,
                worker_kind, est_monthly_budget, justification, reports_to,
                collaborates_with_json, state, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', datetime('now'))""",
            (
                hid, company_id, requested_by, payload["role"],
                payload["team_id"],
                json.dumps(payload.get("skills_required", [])),
                payload.get("worker_kind"),
                payload.get("est_monthly_budget"),
                payload["justification"],
                payload["reports_to"],
                json.dumps(payload.get("collaborates_with", [])),
            ),
        )
        # Create linked issue (spec 03 §1: every task has an issue)
        conn.execute(
            """INSERT INTO issues
               (id, company_id, title, body, type, state,
                assignee_agent, reporter, priority)
               VALUES (?, ?, ?, ?, 'hire', 'open', ?, ?, 'normal')""",
            (
                iid, company_id,
                f"Hire: {payload['role']}",
                payload["justification"],
                None,  # no agent assignee yet — board decides
                requested_by,
            ),
        )
        # Audit
        conn.execute(
            """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
               VALUES (?, datetime('now'), ?, 'hire.requested', ?, ?)""",
            (str(uuid.uuid4()), requested_by, hid,
             json.dumps({
                 "role": payload["role"],
                 "team": payload["team_id"],
                 "est_monthly_budget": payload.get("est_monthly_budget"),
             })),
        )
        conn.commit()
        _bump_hire_rate(requested_by)
    finally:
        conn.close()

    return {
        "status": "pending",
        "hire_id": hid,
        "issue_id": iid,
        "requires": "board approval via /hires/{id}/approve",
    }


# ── Public: approve ────────────────────────────────────────────
def approve_hire(hire_id: str, approver: str) -> Dict[str, Any]:
    """Mark hire approved; INSERT agents(status=inactive) + edges. NO spawn."""
    conn = _db()
    try:
        h = conn.execute(
            "SELECT * FROM hires WHERE id = ?", (hire_id,),
        ).fetchone()
        if not h:
            raise HireRefused(f"hire {hire_id!r} not found")
        if h["state"] != "pending":
            raise HireRefused(f"hire {hire_id!r} state={h['state']!r}, not pending")

        # 1. Create agent as INACTIVE (no auto-spawn, per locked default)
        new_agent_id = f"{h['role'].lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
        worker_kind_val = h["worker_kind"] or "api"
        model_val = "claude_code" if "claude" in worker_kind_val else worker_kind_val
        conn.execute(
            """INSERT INTO agents
               (id, company_id, team_id, name, role, worker_type, status,
                worker_kind, model_binding, monthly_budget_json, hire_rate_json)
               VALUES (?, ?, ?, ?, ?, ?, 'inactive', ?, ?, ?, ?)""",
            (
                new_agent_id, h["company_id"], h["team_id"],
                h["role"].title(), h["role"], worker_kind_val,
                worker_kind_val, model_val,
                json.dumps({"tokens": 1_000_000, "usd": h["est_monthly_budget"] or 5.0,
                            "requests_limit": 200}),
                json.dumps({"count": 0, "window": "24h", "reset_at": None}),
            ),
        )
        # 2. reports_to edge
        if h["reports_to"]:
            conn.execute(
                """INSERT INTO edges (id, company_id, type, from_agent, to_agent)
                   VALUES (?, ?, 'reports_to', ?, ?)""",
                (str(uuid.uuid4()), h["company_id"], new_agent_id, h["reports_to"]),
            )
        # 3. collaborates_with edges
        if h["collaborates_with_json"]:
            try:
                collabs = json.loads(h["collaborates_with_json"])
                for peer in collabs:
                    conn.execute(
                        """INSERT INTO edges (id, company_id, type, from_agent, to_agent)
                           VALUES (?, ?, 'collaborates_with', ?, ?)""",
                        (str(uuid.uuid4()), h["company_id"], new_agent_id, peer),
                    )
            except Exception:
                pass
        # 4. Mark hire approved
        conn.execute(
            """UPDATE hires SET state='approved', approver=?, decided_at=datetime('now')
               WHERE id=?""",
            (approver, hire_id),
        )
        # 5. Update linked issue state
        conn.execute(
            """UPDATE issues SET state='done',
                  updated_at=datetime('now')
               WHERE id = ?""",
            (f"iss-hire-{hire_id}",),
        )
        # 6. Audit
        conn.execute(
            """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
               VALUES (?, datetime('now'), ?, 'hire.approved', ?, ?)""",
            (str(uuid.uuid4()), approver, hire_id,
             json.dumps({"new_agent_id": new_agent_id, "status": "inactive"})),
        )
        conn.commit()

        return {
            "status": "approved",
            "hire_id": hire_id,
            "new_agent_id": new_agent_id,
            "agent_status": "inactive",
            "note": "agent created but NOT spawned; provisioner is disabled by default",
        }
    finally:
        conn.close()


# ── Public: reject ─────────────────────────────────────────────
def reject_hire(hire_id: str, approver: str, reason: str = "") -> Dict[str, Any]:
    conn = _db()
    try:
        h = conn.execute("SELECT * FROM hires WHERE id = ?", (hire_id,)).fetchone()
        if not h:
            raise HireRefused(f"hire {hire_id!r} not found")
        if h["state"] != "pending":
            raise HireRefused(f"hire {hire_id!r} state={h['state']!r}, not pending")
        conn.execute(
            """UPDATE hires SET state='rejected', approver=?, decided_at=datetime('now')
               WHERE id=?""",
            (approver, hire_id),
        )
        conn.execute(
            """UPDATE issues SET state='rejected', updated_at=datetime('now')
               WHERE id = ?""",
            (f"iss-hire-{hire_id}",),
        )
        conn.execute(
            """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
               VALUES (?, datetime('now'), ?, 'hire.rejected', ?, ?)""",
            (str(uuid.uuid4()), approver, hire_id,
             json.dumps({"reason": reason})),
        )
        conn.commit()
        return {"status": "rejected", "hire_id": hire_id, "approver": approver, "reason": reason}
    finally:
        conn.close()


# ── Public: list ───────────────────────────────────────────────
def list_hires(state: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = _db()
    try:
        if state:
            cur = conn.execute(
                "SELECT * FROM hires WHERE state = ? ORDER BY created_at DESC", (state,),
            )
        else:
            cur = conn.execute("SELECT * FROM hires ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
