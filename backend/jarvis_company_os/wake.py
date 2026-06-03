"""jarvis_company_os.wake — Spec 02 §4 wake cycle + wake_lock leader election.

Boss final ruling (D2 applied earlier): wake uses atomic UPDATE WHERE wake_lock=0
to guarantee one concurrent cycle per agent. If rowcount=0 → 409 already waking.

7-step heartbeat (per spec 02 §4.1):
  1. Load open issues for the agent
  2. Read comments on each, identify blockers
  3. Post status comment on top issue
  4. Check inbox for pending approvals
  5. Decide next action: TASK_ASSIGN or ESCALATION
  6. Emit through authorize() (Phase 2)
  7. Release wake_lock, signal liveness
"""
import json
import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("jarvis_company_os.wake")

KANBAN_DB_PATH = Path("/home/ubuntu/.hermes/kanban.db")


def _db() -> sqlite3.Connection:
    c = sqlite3.connect(str(KANBAN_DB_PATH), timeout=5.0)
    c.row_factory = sqlite3.Row
    return c


class WakeConflict(Exception):
    """Raised when wake_lock is already held (concurrent wake)."""
    pass


def acquire_wake_lock(agent_id: str) -> bool:
    """Atomic wake_lock leader election. Returns True if acquired, False if held."""
    conn = _db()
    try:
        cur = conn.execute(
            """UPDATE agents SET wake_lock = 1
               WHERE id = ? AND wake_lock = 0""",
            (agent_id,),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def release_wake_lock(agent_id: str) -> None:
    conn = _db()
    try:
        conn.execute(
            "UPDATE agents SET wake_lock = 0, status='idle' WHERE id = ?",
            (agent_id,),
        )
        conn.commit()
    finally:
        conn.close()


def _open_issues(conn, agent_id: str) -> List[Dict[str, Any]]:
    cur = conn.execute(
        """SELECT id, title, body, type, state, priority, created_at
           FROM issues
           WHERE assignee_agent = ? AND state IN ('open', 'in_progress', 'blocked')
           ORDER BY
             CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1
                           WHEN 'normal' THEN 2 ELSE 3 END,
             created_at ASC
           LIMIT 10""",
        (agent_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def _comments_for(conn, issue_id: str) -> List[Dict[str, Any]]:
    cur = conn.execute(
        """SELECT id, author, body, kind, created_at
           FROM comments WHERE issue_id = ?
           ORDER BY created_at DESC LIMIT 5""",
        (issue_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def _post_status_comment(conn, issue_id: str, author: str, body: str) -> str:
    cid = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO comments (id, issue_id, author, body, kind, created_at)
           VALUES (?, ?, ?, ?, 'status', datetime('now'))""",
        (cid, issue_id, author, body),
    )
    return cid


def _lead_of(conn, agent_id: str) -> Optional[str]:
    cur = conn.execute(
        """SELECT to_agent FROM edges
           WHERE type = 'reports_to' AND from_agent = ? LIMIT 1""",
        (agent_id,),
    )
    r = cur.fetchone()
    return r["to_agent"] if r else None


def run_heartbeat(agent_id: str) -> Dict[str, Any]:
    """The 7-step wake cycle. Caller is responsible for acquire/release.

    Returns a summary dict for the caller / dashboard.
    """
    from .acl import authorize_and_persist
    from . import envelope as env_mod

    # Step 0: check status before waking
    conn = _db()
    try:
        agent = conn.execute(
            "SELECT id, name, status, team_id, company_id FROM agents WHERE id = ?",
            (agent_id,),
        ).fetchone()
        if not agent:
            return {"woke": False, "reason": f"agent {agent_id!r} not found"}
        if agent["status"] in ("draining", "offline"):
            return {"woke": False, "reason": f"agent status={agent['status']!r}"}
    finally:
        conn.close()

    # Step 1-2: read open issues + comments
    conn = _db()
    issues_reviewed: List[Dict[str, Any]] = []
    status_comments: List[str] = []
    decision: Optional[Dict[str, Any]] = None
    inbox_count = 0
    try:
        issues = _open_issues(conn, agent_id)
        for issue in issues:
            comments = _comments_for(conn, issue["id"])
            has_blocker = any(c["kind"] == "blocker" for c in comments)
            issues_reviewed.append({
                "issue_id": issue["id"],
                "state": issue["state"],
                "priority": issue["priority"],
                "has_blocker": has_blocker,
                "comments_count": len(comments),
            })
        # Step 3: post status comment on top issue
        if issues:
            top = issues[0]
            body = (f"WAKE on {agent_id}: reviewing issue {top['id']!r} "
                    f"(state={top['state']}, priority={top['priority']}).")
            if any(i["has_blocker"] for i in issues_reviewed):
                body += " Blocker detected; will escalate."
            cid = _post_status_comment(conn, top["id"], agent_id, body)
            status_comments.append(cid)

        # Step 4: inbox
        cur = conn.execute(
            "SELECT COUNT(*) AS c FROM messages WHERE to_uri LIKE ? AND acked = 0",
            (f"%.{agent_id}",),
        )
        inbox_count = cur.fetchone()["c"]

        # Step 5: decide
        if issues:
            top = issues[0]
            top_meta = next((i for i in issues_reviewed if i["issue_id"] == top["id"]), None)
            if top_meta and top_meta["has_blocker"]:
                # Step 6 path: escalate
                lead = _lead_of(conn, agent_id)
                if lead:
                    decision = {"action": "ESCALATION", "to_lead": lead,
                                "issue_id": top["id"]}
            else:
                decision = {"action": "TASK_ASSIGN_SELF",
                            "issue_id": top["id"]}
    finally:
        conn.close()

    # Step 6: emit through authorize (Phase 2 path)
    envelope_id = None
    if decision and decision["action"] == "ESCALATION" and decision.get("to_lead"):
        env = env_mod.make_envelope(
            from_uri=f"org.jarvis-war-room.{agent['team_id']}.{agent_id}",
            to_uri=f"org.jarvis-war-room.{agent['team_id']}.{decision['to_lead']}",
            type_="ESCALATION",
            payload={
                "blocker": f"Issue {decision['issue_id']!r} blocked on {agent_id}",
                "options": ["unblock by board", "reassign", "lower priority"],
                "issue_id": decision["issue_id"],
            },
            priority="high",
            issue_id=decision["issue_id"],
        )
        result = authorize_and_persist(env)
        envelope_id = env["id"]
        decision["envelope_id"] = env["id"]
        decision["authorized"] = result.allowed
        if not result.allowed:
            decision["deny_reason"] = result.reason
            decision["route_via_lead"] = result.route

    # Step 7: liveness + audit
    # last_liveness_at lives on the nodes table (spec 04 §1); update there
    conn = _db()
    try:
        conn.execute(
            """UPDATE nodes SET last_liveness_at = datetime('now')
               WHERE id = (SELECT node_id FROM agents WHERE id = ?)""",
            (agent_id,),
        )
        conn.execute(
            """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
               VALUES (?, datetime('now'), ?, 'wake_cycle', ?, ?)""",
            (str(uuid.uuid4()), agent_id, agent_id,
             json.dumps({
                 "issues_reviewed": len(issues_reviewed),
                 "status_comments": len(status_comments),
                 "inbox_count": inbox_count,
                 "decision": decision,
             }, default=str)),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "woke": True,
        "agent": agent_id,
        "issues_reviewed": issues_reviewed,
        "status_comments_posted": status_comments,
        "inbox_count": inbox_count,
        "decision": decision,
        "envelope_id": envelope_id,
    }


def manual_wake(agent_id: str) -> Dict[str, Any]:
    """Public entrypoint: acquire lock, run, release. 409 on conflict."""
    if not acquire_wake_lock(agent_id):
        raise WakeConflict(f"agent {agent_id!r} already waking")
    try:
        return run_heartbeat(agent_id)
    finally:
        release_wake_lock(agent_id)
