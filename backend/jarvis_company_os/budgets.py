"""jarvis_company_os.budgets — Spec 03 §3 budget enforcement + analytics.

3 enforcement points per spec 03 §3.2:
  1. ASSIGN: rule 6 in authorize() (acl.py) — TASK_ASSIGN request-budget gate
  2. SPAWN:  check_spawn() — called before any worker process starts (used in runs/ wake)
  3. HIRE:   check_hire() — called inside hiring.py before INSERT
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger("jarvis_company_os.budgets")

KANBAN_DB_PATH = Path("/home/ubuntu/.hermes/kanban.db")


def _db() -> sqlite3.Connection:
    c = sqlite3.connect(str(KANBAN_DB_PATH), timeout=5.0)
    c.row_factory = sqlite3.Row
    return c


class BudgetExceeded(Exception):
    """Raised when a budget gate refuses an action."""


# ── Gate 2: spawn ──────────────────────────────────────────────
def check_spawn(agent_id: str) -> None:
    """Called before spawning a worker (Hermes delegation, run start).

    Checks team+company token/USD budgets. Subscription workers (claude_code|codex)
    are already gated by rule 6 in authorize() at assign time; this is a
    second-line check for token-budgeted workers.
    """
    conn = _db()
    try:
        # Get agent's company + team
        row = conn.execute(
            "SELECT company_id, team_id FROM agents WHERE id = ?", (agent_id,),
        ).fetchone()
        if not row:
            raise BudgetExceeded(f"agent {agent_id!r} not found")
        company_id = row["company_id"]
        team_id = row["team_id"]

        # Company budget
        crow = conn.execute(
            """SELECT tokens_limit, tokens_used, usd_limit, usd_used
               FROM budgets WHERE scope='company' AND scope_id=?""",
            (company_id,),
        ).fetchone()
        if crow and crow["tokens_limit"] is not None:
            if (crow["tokens_used"] or 0) >= crow["tokens_limit"]:
                raise BudgetExceeded(
                    f"company {company_id!r} at token budget cap "
                    f"({crow['tokens_used']}/{crow['tokens_limit']})"
                )
        if crow and crow["usd_limit"] is not None:
            if (crow["usd_used"] or 0) >= crow["usd_limit"]:
                raise BudgetExceeded(
                    f"company {company_id!r} at USD budget cap "
                    f"({crow['usd_used']}/{crow['usd_limit']})"
                )
        # Team budget
        trow = conn.execute(
            """SELECT tokens_limit, tokens_used
               FROM budgets WHERE scope='team' AND scope_id=?""",
            (team_id,),
        ).fetchone()
        if trow and trow["tokens_limit"] is not None:
            if (trow["tokens_used"] or 0) >= trow["tokens_limit"]:
                raise BudgetExceeded(
                    f"team {team_id!r} at token budget cap "
                    f"({trow['tokens_used']}/{trow['tokens_limit']})"
                )
    finally:
        conn.close()


# ── Gate 3: hire (also re-implemented in hiring.py for explicitness) ─
def check_hire(company_id: str, est_monthly_budget: Optional[float]) -> None:
    conn = _db()
    try:
        if est_monthly_budget is None:
            return
        row = conn.execute(
            """SELECT usd_limit, usd_used FROM budgets
               WHERE scope='company' AND scope_id=?""",
            (company_id,),
        ).fetchone()
        if row and row["usd_limit"] is not None:
            if (row["usd_used"] or 0) + est_monthly_budget > row["usd_limit"]:
                raise BudgetExceeded(
                    f"hire ${est_monthly_budget}/mo would exceed company budget "
                    f"({row['usd_used']}/{row['usd_limit']} USD used)"
                )
    finally:
        conn.close()


# ── Spend recording ────────────────────────────────────────────
def record_spend(scope: str, scope_id: str,
                 tokens_in: int = 0, tokens_out: int = 0,
                 usd: float = 0.0, requests: int = 0) -> None:
    """Called after a run completes to update budgets."""
    conn = _db()
    try:
        conn.execute(
            """UPDATE budgets SET
                  tokens_used = COALESCE(tokens_used, 0) + ?,
                  usd_used    = COALESCE(usd_used, 0) + ?,
                  requests_used = COALESCE(requests_used, 0) + ?
               WHERE scope = ? AND scope_id = ?""",
            (tokens_in + tokens_out, usd, requests, scope, scope_id),
        )
        conn.commit()
    finally:
        conn.close()


# ── Analytics ──────────────────────────────────────────────────
def analytics(scope: str = "agent", period: str = "monthly") -> Dict[str, Any]:
    """Per-scope spend summary. Used by /budgets/analytics endpoint."""
    conn = _db()
    try:
        cur = conn.execute(
            """SELECT id, scope_id, tokens_limit, tokens_used, usd_limit,
                      usd_used, requests_limit, requests_used
               FROM budgets WHERE scope = ? AND period = ?""",
            (scope, period),
        )
        rows = [dict(r) for r in cur.fetchall()]
        total_used_usd = sum(r["usd_used"] or 0 for r in rows)
        total_limit_usd = sum(r["usd_limit"] or 0 for r in rows)
        total_used_tokens = sum(r["tokens_used"] or 0 for r in rows)
        total_limit_tokens = sum(r["tokens_limit"] or 0 for r in rows)
        total_used_req = sum(r["requests_used"] or 0 for r in rows)
        total_limit_req = sum(r["requests_limit"] or 0 for r in rows)
        # Top spenders
        top = sorted(rows, key=lambda r: -(r["usd_used"] or 0))[:5]
        return {
            "scope": scope,
            "period": period,
            "count": len(rows),
            "usd": {"used": total_used_usd, "limit": total_limit_usd,
                    "remaining": (total_limit_usd or 0) - total_used_usd},
            "tokens": {"used": total_used_tokens, "limit": total_limit_tokens,
                       "remaining": (total_limit_tokens or 0) - total_used_tokens},
            "requests": {"used": total_used_req, "limit": total_limit_req,
                         "remaining": (total_limit_req or 0) - total_used_req},
            "top_spenders": top,
        }
    finally:
        conn.close()
