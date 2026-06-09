"""jarvis_company_os.router — FastAPI routes for spec 04 spine (Phase 1+2).

Mounted at /api/plugins/jarvis-dashboard/v1/companies, /edges, /topology, /messages.
Phase 1 endpoints: topology, companies, edges, admin/apply-migrations, admin/seed.
Phase 2 endpoints: messages, messages/inbox, admin/control-token-info.
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from . import registry
from .migrations import apply_pending
from . import envelope as env_mod
from .acl import authorize_and_persist, sign_control_token, _load_control_token
from . import wake as wake_mod
from . import gen_agent_files as gen_files_mod
from . import hiring as hiring_mod
from . import budgets as budgets_mod
from . import spawn as spawn_mod

log = logging.getLogger("jarvis_company_os.router")
router = APIRouter()


@router.get("/companies/{company_id}/topology")
def get_company_topology(company_id: str):
    """Boss D4 acceptance: response shape {nodes, agents, edges}."""
    try:
        return registry.get_topology(company_id)
    except Exception as e:
        log.exception("get_topology failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/companies")
def create_company(payload: dict):
    cid = payload.get("id") or f"co-{uuid.uuid4().hex[:8]}"
    try:
        import sqlite3
        conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
        try:
            conn.execute(
                """INSERT INTO companies
                   (id, name, mission, goal, status, budget_tokens, budget_usd,
                    policy_json, require_board_approval, max_headcount, max_org_depth)
                   VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)""",
                (
                    cid,
                    payload.get("name", cid),
                    payload.get("mission"),
                    payload.get("goal"),
                    payload.get("budget_tokens"),
                    payload.get("budget_usd"),
                    str(payload.get("policy_json", "{}")),
                    int(payload.get("require_board_approval", 1)),
                    payload.get("max_headcount"),
                    payload.get("max_org_depth"),
                ),
            )
            conn.commit()
            return {"id": cid, "status": "created"}
        finally:
            conn.close()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/edges")
def add_edge(payload: dict):
    if "type" not in payload or "from_agent" not in payload or "to_agent" not in payload:
        raise HTTPException(status_code=400,
                            detail="required: type, from_agent, to_agent")
    if payload["type"] not in ("reports_to", "collaborates_with"):
        raise HTTPException(status_code=400,
                            detail="type must be reports_to or collaborates_with")
    eid = payload.get("id") or str(uuid.uuid4())
    company_id = payload.get("company_id", "jarvis-war-room")
    from_agent = payload["from_agent"]
    to_agent = payload["to_agent"]

    # D-2026-06-08 sub-phase 3: cycle prevention on reports_to.
    # Reject self-loops and any path that would close a cycle.
    if payload["type"] == "reports_to":
        if _edge_would_form_cycle(company_id, from_agent, to_agent):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"reports_to edge {from_agent!r} -> {to_agent!r} would "
                    f"form a cycle in the org hierarchy"
                ),
            )

    try:
        import sqlite3
        conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
        try:
            conn.execute(
                """INSERT INTO edges (id, company_id, type, from_agent, to_agent)
                   VALUES (?, ?, ?, ?, ?)""",
                (eid, company_id, payload["type"],
                 from_agent, to_agent),
            )
            conn.execute(
                """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
                   VALUES (?, datetime('now'), 'jarvis-company-os', 'edge.add',
                           ?, ?)""",
                (str(uuid.uuid4()), eid,
                 f'{{"type":"{payload["type"]}",'
                 f'"from":"{from_agent}",'
                 f'"to":"{to_agent}"}}'),
            )
            conn.commit()
            return {"id": eid, "status": "created"}
        finally:
            conn.close()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _edge_would_form_cycle(company_id: str, from_agent: str, to_agent: str) -> bool:
    """Return True if adding `from_agent -> to_agent` (reports_to) would
    create a cycle in the org hierarchy. Used by add_edge() to enforce
    the tree property.

    Algorithm (per codex design 2026-06-08):
      1. Self-loop is always a cycle.
      2. Build the reports_to graph from existing edges.
      3. DFS from to_agent. If we can reach from_agent, the new edge
         would close a cycle.
    """
    if from_agent == to_agent:
        return True
    import sqlite3
    from collections import defaultdict
    graph: dict = defaultdict(list)
    db_path, _ = registry._resolve_paths()
    with sqlite3.connect(str(db_path), timeout=5.0) as conn:
        rows = conn.execute(
            """SELECT from_agent, to_agent FROM edges
               WHERE company_id = ? AND type = 'reports_to'""",
            (company_id,),
        ).fetchall()
    for src, dst in rows:
        graph[src].append(dst)
    visited = set()

    def dfs(agent: str) -> bool:
        if agent == from_agent:
            return True
        if agent in visited:
            return False
        visited.add(agent)
        for nxt in graph.get(agent, []):
            if dfs(nxt):
                return True
        return False

    return dfs(to_agent)


@router.delete("/edges/{edge_id}")
def delete_edge(edge_id: str):
    import sqlite3
    db_path, _ = registry._resolve_paths()
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    try:
        cur = conn.execute("DELETE FROM edges WHERE id = ?", (edge_id,))
        if cur.rowcount == 0:
            # Nothing to delete — return 404 BEFORE committing the audit log
            raise HTTPException(status_code=404, detail="edge not found")
        conn.execute(
            """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
               VALUES (?, datetime('now'), 'jarvis-company-os', 'edge.remove', ?, '{}')""",
            (str(uuid.uuid4()), edge_id),
        )
        conn.commit()
        return {"id": edge_id, "status": "removed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.post("/admin/apply-migrations")
def admin_apply_migrations():
    """Manual migration trigger (in case lifespan didn't run)."""
    try:
        results = apply_pending()
        return {"applied": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/seed")
def admin_seed():
    """Manual seed trigger (in case lifespan didn't seed; safe — idempotent)."""
    try:
        return registry.seed_default_company()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Phase 2 endpoints (Envelope + authorize) ──────────────────

@router.post("/messages")
def post_message(payload: dict):
    """POST a bus message. Validates envelope, calls authorize_and_persist(),
    writes messages + comments + audit_log rows as required.
    """
    # 1. Validate envelope (400 on schema violation).
    #    Auto-fill id/created_at if missing (common case for dashboard-side POSTs).
    import uuid as _uuid
    from datetime import datetime, timezone
    payload = dict(payload)  # don't mutate caller's dict
    if "id" not in payload:
        payload["id"] = str(_uuid.uuid4())
    if "created_at" not in payload:
        payload["created_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        env_mod.validate(payload)
    except env_mod.EnvelopeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Auto-sign CONTROL messages if they originate from the control node
    #    (recognize by URI pattern org.<co>.control)
    if payload["type"] == "CONTROL" and payload["from"].endswith(".control"):
        if not payload.get("control_token"):
            payload["control_token"] = sign_control_token(payload["id"])

    # 3. authorize + persist (Boss D1 rule 6 enforced inside)
    result = authorize_and_persist(payload)
    if not result.allowed:
        return {
            "delivered": False,
            "allowed": False,
            "reason": result.reason,
            "rule": result.rule,
            "route_via_lead": result.route,
            "audit_id": result.audit_id,
        }
    return {
        "delivered": True,
        "allowed": True,
        "rule": result.rule,
        "reason": result.reason,
        "audit_id": result.audit_id,
        "envelope_id": payload["id"],
    }


@router.get("/messages/inbox")
def inbox(agent_id: str = Query(...), limit: int = 50):
    """List messages addressed to this agent, newest first."""
    import sqlite3
    conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """SELECT id, conversation_id, trace_id, issue_id, from_uri, to_uri,
                      type, priority, payload_json, artifacts_json, task_state,
                      created_at, delivered, acked
               FROM messages
               WHERE to_uri LIKE ?
               ORDER BY created_at DESC LIMIT ?""",
            (f"%.{agent_id}", limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
        # parse json cols
        import json
        for r in rows:
            for col in ("payload_json", "artifacts_json"):
                v = r.get(col)
                if v and isinstance(v, str):
                    try:
                        r[col] = json.loads(v)
                    except Exception:
                        pass
        return {"agent": agent_id, "count": len(rows), "messages": rows}
    finally:
        conn.close()


@router.get("/messages/audit")
def messages_audit(limit: int = 100):
    """Audit log feed for council/dashboard inspection."""
    import sqlite3, json
    conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """SELECT id, ts, actor, action, target, detail_json
               FROM audit_log
               WHERE actor LIKE 'org.%' OR actor = 'jarvis-company-os'
                  OR action LIKE 'auth_%' OR action LIKE 'CONTROL_%'
                  OR action LIKE 'request_%' OR action LIKE 'edge.%'
               ORDER BY ts DESC LIMIT ?""",
            (limit,),
        )
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            v = r.get("detail_json")
            if v and isinstance(v, str):
                try:
                    r["detail_json"] = json.loads(v)
                except Exception:
                    pass
        return {"count": len(rows), "rows": rows}
    finally:
        conn.close()


@router.get("/admin/control-token-info")
def control_token_info():
    """Diagnostic: is JARVIS_CONTROL_TOKEN set? (NEVER return the token value.)"""
    tok = _load_control_token()
    return {
        "set": bool(tok),
        "length": len(tok),
        "warning": ("unset — CONTROL gate will deny all CONTROL messages"
                    if not tok else "configured"),
    }


@router.post("/admin/issue-control-token")
def issue_control_token(payload: dict):
    """Mint a signed control_token for a new envelope id (for the control node)."""
    eid = payload.get("envelope_id") or str(uuid.uuid4())
    sig = sign_control_token(eid)
    return {"envelope_id": eid, "control_token": sig}


# ── Phase 3 endpoints (Four Files + Manual Wake) ───────────────

@router.post("/agents/{agent_id}/wake")
def wake_agent(agent_id: str):
    """Spec 02 §4. Manual wake trigger. Uses wake_lock leader election.

    Returns 409 if another wake is in flight.
    """
    try:
        result = wake_mod.manual_wake(agent_id)
        return result
    except wake_mod.WakeConflict as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        log.exception("wake failed for %s", agent_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/wake-status")
def wake_status(agent_id: str):
    """Read current wake_lock state for an agent + node liveness."""
    import sqlite3
    conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """SELECT a.id, a.status, a.wake_lock, n.last_liveness_at
               FROM agents a LEFT JOIN nodes n ON a.node_id = n.id
               WHERE a.id = ?""",
            (agent_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"agent {agent_id!r} not found")
        return dict(row)
    finally:
        conn.close()


@router.post("/admin/generate-agent-files")
def admin_generate_agent_files():
    """Phase 3: write HEARTBEAT.md/TOOLS.md/AGENTS.md for every agent."""
    try:
        return gen_files_mod.generate_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/files")
def get_agent_files(agent_id: str):
    """Read back the generated 4 files for an agent (Phase 3 verification)."""
    import sqlite3
    conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """SELECT id, soul_path, heartbeat_path, tools_path, agents_path
               FROM agents WHERE id = ?""",
            (agent_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"agent {agent_id!r} not found")
        out = {"agent_id": agent_id, "files": {}}
        for label, key in (("SOUL", "soul_path"), ("HEARTBEAT", "heartbeat_path"),
                           ("TOOLS", "tools_path"), ("AGENTS", "agents_path")):
            p = row[key]
            if p:
                from pathlib import Path
                f = Path(p)
                if f.exists():
                    out["files"][label] = {
                        "path": str(f),
                        "size": f.stat().st_size,
                        "first_line": f.read_text().splitlines()[0] if f.read_text() else "",
                    }
                else:
                    out["files"][label] = {"path": p, "exists": False}
        return out
    finally:
        conn.close()


# ── Phase 4 endpoints (Hiring + Issues + Inbox + Analytics) ────

@router.post("/hires")
def post_hire(payload: dict):
    """Submit a HIRE_REQUEST. Runs 3 guardrails (rate, headcount, budget)."""
    try:
        return hiring_mod.submit_hire(payload)
    except hiring_mod.HireRefused as e:
        raise HTTPException(status_code=402, detail=str(e))
    except Exception as e:
        log.exception("submit_hire failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hires")
def list_hires(state: str = None):
    return {"hires": hiring_mod.list_hires(state=state)}


@router.post("/hires/{hire_id}/approve")
def approve_hire(hire_id: str, payload: dict = None):
    payload = payload or {}
    approver = payload.get("approver", "board")
    try:
        return hiring_mod.approve_hire(hire_id, approver)
    except hiring_mod.HireRefused as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/hires/{hire_id}/reject")
def reject_hire(hire_id: str, payload: dict = None):
    payload = payload or {}
    approver = payload.get("approver", "board")
    reason = payload.get("reason", "")
    try:
        return hiring_mod.reject_hire(hire_id, approver, reason)
    except hiring_mod.HireRefused as e:
        raise HTTPException(status_code=409, detail=str(e))


# ── Issues board (spec 03 §1) ─────────────────────────────────
@router.get("/issues")
def list_issues(state: str = None, assignee: str = None, type: str = None,
                company_id: str = "jarvis-war-room", limit: int = 100):
    import sqlite3, json
    conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        where = ["company_id = ?"]
        params = [company_id]
        if state:
            where.append("state = ?")
            params.append(state)
        if assignee:
            where.append("assignee_agent = ?")
            params.append(assignee)
        if type:
            where.append("type = ?")
            params.append(type)
        q = f"""SELECT id, title, body, type, state, assignee_agent, reporter,
                       priority, created_at, updated_at FROM issues
                WHERE {' AND '.join(where)}
                ORDER BY
                  CASE state WHEN 'blocked' THEN 0 WHEN 'open' THEN 1
                             WHEN 'in_progress' THEN 2 WHEN 'in_review' THEN 3
                             ELSE 4 END,
                  CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1
                                WHEN 'normal' THEN 2 ELSE 3 END,
                  created_at DESC LIMIT ?"""
        params.append(limit)
        cur = conn.execute(q, params)
        rows = [dict(r) for r in cur.fetchall()]
        # Attach comments for each
        for r in rows:
            cc = conn.execute(
                "SELECT id, author, body, kind, created_at FROM comments "
                "WHERE issue_id = ? ORDER BY created_at ASC",
                (r["id"],),
            ).fetchall()
            r["comments"] = [dict(x) for x in cc]
        return {"count": len(rows), "issues": rows}
    finally:
        conn.close()


@router.post("/issues")
def create_issue(payload: dict):
    import sqlite3, uuid as _uuid
    conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
    try:
        iid = payload.get("id") or f"iss-{_uuid.uuid4().hex[:8]}"
        conn.execute(
            """INSERT INTO issues
               (id, company_id, project_id, milestone_id, title, body, type, state,
                assignee_agent, reporter, priority, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
            (
                iid,
                payload.get("company_id", "jarvis-war-room"),
                payload.get("project_id"),
                payload.get("milestone_id"),
                payload["title"],
                payload.get("body"),
                payload.get("type", "task"),
                payload.get("state", "open"),
                payload.get("assignee_agent"),
                payload.get("reporter", "board"),
                payload.get("priority", "normal"),
            ),
        )
        conn.commit()
        return {"id": iid, "status": "created"}
    finally:
        conn.close()


@router.post("/issues/{issue_id}/comments")
def post_comment(issue_id: str, payload: dict):
    import sqlite3, uuid as _uuid, json
    conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
    try:
        cid = str(_uuid.uuid4())
        conn.execute(
            """INSERT INTO comments
               (id, issue_id, author, body, kind, created_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            (cid, issue_id, payload.get("author", "board"),
             payload.get("body", ""), payload.get("kind", "comment")),
        )
        # Audit
        conn.execute(
            """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
               VALUES (?, datetime('now'), ?, 'comment.posted', ?, ?)""",
            (str(_uuid.uuid4()), payload.get("author", "board"), issue_id,
             json.dumps({"kind": payload.get("kind", "comment")})),
        )
        conn.commit()
        return {"id": cid, "issue_id": issue_id, "status": "created"}
    finally:
        conn.close()


# ── Inbox (board approvals + blockers) ────────────────────────
@router.get("/inbox")
def board_inbox(limit: int = 50):
    """Items needing board attention: pending hires, blocked issues, recent denials."""
    import sqlite3, json
    conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        out = {"pending_hires": [], "blocked_issues": [], "recent_denials": []}
        # Pending hires
        for r in conn.execute(
            "SELECT id, role, team_id, justification, est_monthly_budget, "
            "requested_by, created_at FROM hires WHERE state='pending' "
            "ORDER BY created_at DESC LIMIT ?", (limit,),
        ).fetchall():
            out["pending_hires"].append(dict(r))
        # Blocked issues
        for r in conn.execute(
            "SELECT id, title, assignee_agent, priority, updated_at "
            "FROM issues WHERE state='blocked' ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall():
            out["blocked_issues"].append(dict(r))
        # Recent auth denials
        for r in conn.execute(
            "SELECT ts, actor, target, detail_json FROM audit_log "
            "WHERE action LIKE 'auth_deny%' OR action='CONTROL_gate_deny' "
            "ORDER BY ts DESC LIMIT ?", (limit,),
        ).fetchall():
            d = dict(r)
            if d.get("detail_json"):
                try:
                    d["detail_json"] = json.loads(d["detail_json"])
                except Exception:
                    pass
            out["recent_denials"].append(d)
        return out
    finally:
        conn.close()


# ── Budgets analytics ─────────────────────────────────────────
@router.get("/budgets/analytics")
def budgets_analytics(scope: str = "agent", period: str = "monthly"):
    return budgets_mod.analytics(scope=scope, period=period)


# ── Projects + Milestones ─────────────────────────────────────
@router.post("/projects")
def create_project(payload: dict):
    import sqlite3, uuid as _uuid
    conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
    try:
        pid = payload.get("id") or f"proj-{_uuid.uuid4().hex[:8]}"
        conn.execute(
            """INSERT INTO projects (id, company_id, name, description)
               VALUES (?, ?, ?, ?)""",
            (pid, payload.get("company_id", "jarvis-war-room"),
             payload["name"], payload.get("description")),
        )
        conn.commit()
        return {"id": pid, "status": "created"}
    finally:
        conn.close()


@router.post("/milestones")
def create_milestone(payload: dict):
    import sqlite3, uuid as _uuid
    conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
    try:
        mid = payload.get("id") or f"ms-{_uuid.uuid4().hex[:8]}"
        conn.execute(
            """INSERT INTO milestones
               (id, company_id, project_id, name, goal, due, status)
               VALUES (?, ?, ?, ?, ?, ?, 'active')""",
            (mid, payload.get("company_id", "jarvis-war-room"),
             payload.get("project_id"), payload["name"],
             payload.get("goal"), payload.get("due")),
        )
        conn.commit()
        return {"id": mid, "status": "created"}
    finally:
        conn.close()


# ── Runs (spec 04 §2) ─────────────────────────────────────────
@router.get("/runs")
def list_runs(agent_id: str = None, status: str = None, limit: int = 50):
    import sqlite3
    conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        where, params = [], []
        if agent_id:
            where.append("agent_id = ?")
            params.append(agent_id)
        if status:
            where.append("status = ?")
            params.append(status)
        q = f"SELECT run_id, agent_id, issue_id, worker_kind, repo, branch, status, started_at, finished_at FROM runs"
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        return {"runs": [dict(r) for r in conn.execute(q, params).fetchall()]}
    finally:
        conn.close()


@router.post("/runs/{run_id}/approve")
def approve_run(run_id: str, payload: dict = None):
    """Spec 01 §4.7: board approves a completed run → marks done, decrements budget."""
    import sqlite3, json
    payload = payload or {}
    conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        run = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,),
        ).fetchone()
        if not run:
            raise HTTPException(status_code=404, detail="run not found")
        # Budget gate: check before approving
        try:
            budgets_mod.check_spawn(run["agent_id"])
        except budgets_mod.BudgetExceeded as e:
            conn.execute(
                """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
                   VALUES (?, datetime('now'), 'board', 'run.approve.refused',
                           ?, ?)""",
                (str(__import__('uuid').uuid4()), run_id, json.dumps({"reason": str(e)})),
            )
            conn.commit()
            raise HTTPException(status_code=402, detail=f"budget gate: {e}")
        # Mark approved
        conn.execute(
            "UPDATE runs SET status='approved' WHERE run_id = ?", (run_id,),
        )
        # Mark linked issue done
        if run["issue_id"]:
            conn.execute(
                "UPDATE issues SET state='done', updated_at=datetime('now') "
                "WHERE id = ?", (run["issue_id"],),
            )
        # Audit
        conn.execute(
            """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
               VALUES (?, datetime('now'), 'board', 'run.approved', ?, '{}')""",
            (str(__import__('uuid').uuid4()), run_id),
        )
        conn.commit()
        return {"run_id": run_id, "status": "approved"}
    finally:
        conn.close()


@router.post("/runs/{run_id}/reject")
def reject_run(run_id: str, payload: dict = None):
    import sqlite3, json
    payload = payload or {}
    reason = payload.get("reason", "rejected by board")
    conn = sqlite3.connect(str(registry._resolve_paths()[0]), timeout=5.0)
    try:
        conn.execute(
            "UPDATE runs SET status='rejected', reject_reason=? WHERE run_id=?",
            (reason, run_id),
        )
        conn.execute(
            """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
               VALUES (?, datetime('now'), 'board', 'run.rejected', ?, ?)""",
            (str(__import__('uuid').uuid4()), run_id, json.dumps({"reason": reason})),
        )
        conn.commit()
        return {"run_id": run_id, "status": "rejected", "reason": reason}
    finally:
        conn.close()


# ── Phase 5 endpoints (spawn_worker LITE) ──────────────────────

@router.post("/runs/{run_id}/execute")
def execute_run(run_id: str, payload: dict = None):
    """Spec 04 §5 step 5: spawn codex in a worktree. Status -> running -> complete|failed.

    Body: {"timeout": 300} (optional, defaults to JARVIS_SPAWN_TIMEOUT env or 300).
    """
    payload = payload or {}
    timeout = int(payload.get("timeout", spawn_mod.DEFAULT_TIMEOUT_SECONDS))
    try:
        return spawn_mod.execute_run(run_id, timeout=timeout)
    except spawn_mod.SpawnRefused as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        log.exception("execute_run failed for %s", run_id)
        raise HTTPException(status_code=500, detail=str(e))
