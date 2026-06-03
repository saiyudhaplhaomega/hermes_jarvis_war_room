#!/usr/bin/env python3
"""gen_agent_files.py — Generate HEARTBEAT.md, TOOLS.md, AGENTS.md for all 14 profiles.

Phase 3 deliverable. Reads seeded agents from the spec 04 DB, walks the edges
graph to build reports_to/collaborates_with rosters, writes 42 markdown files
to ~/.hermes/agents/<slug>/. Idempotent.
"""
import sqlite3
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, List, Any

log = logging.getLogger("jarvis_company_os.gen_agent_files")

KANBAN_DB_PATH = Path("/home/ubuntu/.hermes/kanban.db")
AGENTS_HOME = Path("/home/ubuntu/.hermes/agents")

TEMPLATES = {
    "HEARTBEAT.md": """# HEARTBEAT — {agent_name}

> Spec 02 §2 + §4.1 — 7-step wake checklist for {slug}
> Schedule: {heartbeat_schedule}
> Worker kind: {worker_kind}  |  Model: {model_binding}

## On WAKE (manual or scheduled):

1. **Load context.** Read `~/.hermes/memory/MEMORY.md` + recent sessions via FTS5 session search.
   Re-read this `HEARTBEAT.md`, your `SOUL.md`, and your `AGENTS.md` (roster).
2. **Read open issues.** `GET /api/plugins/jarvis-dashboard/v1/issues?assignee={slug}&state=open`
   Walk each issue: read latest `comments` table rows; identify `kind='blocker'` rows.
3. **Post a status comment** on the top issue: `POST /issues/{id}/comments` kind=`status`.
   Body: what you're doing + what you need.
4. **Check inbox.** `GET /messages/inbox?agent_id={slug}` for pending approvals, escalations, queries.
5. **Decide next action**:
   - If unblocked issue exists with `priority in (high, urgent)`: emit TASK_ASSIGN via `POST /messages`.
   - If blocked: emit ESCALATION upward to your lead (see AGENTS.md).
   - If you are a manager: consider HIRE_REQUEST if the team is overloaded.
6. **Emit message** (rule 5 in `authorize()`): `POST /messages` — always goes through `acl.authorize_and_persist()`.
7. **Signal liveness + release wake_lock**:
   - `UPDATE agents SET wake_lock=0, status='idle' WHERE id='{slug}'` (atomic)
   - `POST /liveness` (optional)
   - Persist what you learned to memory.

## Forbidden during wake
- No shell exec outside the worktree.
- No `POST /nodes/scale` without a board-approved issue.
- No autonomous hire without explicit Saiyudh approval.

## Concurrency
Wake uses atomic `UPDATE agents SET wake_lock=1 WHERE id=? AND wake_lock=0`. If `rowcount=0` another
cycle is already running → return 409. Only one wake per agent at a time.
""",
    "TOOLS.md": """# TOOLS — {agent_name}

> Spec 02 §2 — capabilities and forbidden surface for {slug}

## Worker
- **worker_kind:** {worker_kind}
- **model:** {model_binding}

## Skills (assigned via agent_skills table)
- (populated when skills are attached; see /api/plugins/jarvis-dashboard/v1/agents/{{id}}/skills)

## Allowed capabilities
- `task_read`, `task_write` (own tasks)
- `comment_post` (own + team-visible)
- `memory_read`, `memory_write` (own vault + shared)
- `message_send` (subject to authorize() ACL)
- `escalate_send` (vertical up)
- `liveness_ping`

## Forbidden
- `shell_exec` outside the worktree assigned to a run.
- `node_provision` (no `POST /nodes/scale`) without a board-approved issue.
- `autonomous_hire` — no `POST /hires` from this agent. Only board members approve hires.
- `drain_node`, `kill_node` — these are CONTROL messages, require HMAC `JARVIS_CONTROL_TOKEN`.
- Direct DB writes outside the spec 04 schema boundary.

## MCP / External
- (populated as MCP servers are attached via `jarvis_company_os.skills.attach_mcp()`)
""",
    "AGENTS.md": """# AGENTS — {agent_name}

> Spec 02 §2 — human-readable roster (auto-generated from edges table).
> Regenerated whenever edges change. Re-run: `python3 -m jarvis_company_os.gen_agent_files`.

I am **{agent_name}** ({slug}).
Company: {company_id}  |  Team: {team_id}  |  Node: {node_id}

## I report to
{reports_to_list}

## I manage (people who report to me)
{manages_list}

## I collaborate with
{collaborates_list}

## Teammates on my team ({team_id})
{team_mates_list}

## How to message
- Use `POST /api/plugins/jarvis-dashboard/v1/messages` with the spec 01 §4.3 envelope.
- URIs: `org.{company}.{team}.{agent_id}`.
- All messages go through `authorize()` — check `AGENTS.md` first to avoid denials.
- Cross-team: send to your lead (escalation up) and ask them to route.
""",
}


def _fetch_agent(conn, slug: str) -> Dict[str, Any]:
    cur = conn.execute(
        """SELECT id, company_id, team_id, node_id, name, role, worker_type,
                  worker_kind, model_binding, heartbeat_schedule
           FROM agents WHERE id = ?""",
        (slug,),
    )
    row = cur.fetchone()
    return dict(row) if row else {}


def _edges_for(conn, slug: str) -> Dict[str, List[str]]:
    """Return {reports_to: [...], manages: [...], collaborates_with: [...]}."""
    out = {"reports_to": [], "manages": [], "collaborates_with": []}
    cur = conn.execute(
        "SELECT to_agent FROM edges WHERE type='reports_to' AND from_agent=?",
        (slug,),
    )
    out["reports_to"] = [r["to_agent"] for r in cur.fetchall()]
    cur = conn.execute(
        "SELECT from_agent FROM edges WHERE type='reports_to' AND to_agent=?",
        (slug,),
    )
    out["manages"] = [r["from_agent"] for r in cur.fetchall()]
    cur = conn.execute(
        """SELECT CASE WHEN from_agent=? THEN to_agent ELSE from_agent END AS peer
           FROM edges WHERE type='collaborates_with'
             AND (from_agent=? OR to_agent=?)""",
        (slug, slug, slug),
    )
    out["collaborates_with"] = [r["peer"] for r in cur.fetchall()]
    return out


def _team_mates(conn, team_id: str, exclude_slug: str) -> List[str]:
    cur = conn.execute(
        "SELECT id FROM agents WHERE team_id=? AND id != ?",
        (team_id, exclude_slug),
    )
    return [r["id"] for r in cur.fetchall()]


def _format_bullets(items: List[str], empty_msg: str = "_(none)_") -> str:
    if not items:
        return empty_msg
    return "\n".join(f"- `{x}`" for x in items)


def _safe_format(template: str, **kwargs) -> str:
    """str.format but only substitutes {name} where name is in kwargs; leaves
    all other {x} sequences alone. Avoids the KeyError on stray braces from
    inline code examples like {id} in a URL or `{x,y}` placeholders."""
    import re
    valid = set(kwargs.keys())

    def repl(m):
        key = m.group(1)
        if key in valid:
            return str(kwargs[key])
        return m.group(0)  # leave as-is

    return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", repl, template)


def generate_all() -> Dict[str, Any]:
    """Write HEARTBEAT.md, TOOLS.md, AGENTS.md for every agent in the DB."""
    if not KANBAN_DB_PATH.exists():
        return {"status": "skipped", "reason": "kanban.db missing"}

    conn = sqlite3.connect(str(KANBAN_DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    written = []
    try:
        cur = conn.execute("SELECT id FROM agents ORDER BY id")
        slugs = [r["id"] for r in cur.fetchall()]

        for slug in slugs:
            agent = _fetch_agent(conn, slug)
            edges = _edges_for(conn, slug)
            team_mates = _team_mates(conn, agent.get("team_id") or "default", slug)
            agent_dir = AGENTS_HOME / slug
            agent_dir.mkdir(parents=True, exist_ok=True)

            # HEARTBEAT.md
            hb_path = agent_dir / "HEARTBEAT.md"
            hb_path.write_text(_safe_format(TEMPLATES["HEARTBEAT.md"],
                agent_name=agent.get("name") or slug,
                slug=slug,
                heartbeat_schedule=agent.get("heartbeat_schedule") or "(manual only)",
                worker_kind=agent.get("worker_kind") or "api",
                model_binding=agent.get("model_binding") or "unknown",
            ))

            # TOOLS.md
            tools_path = agent_dir / "TOOLS.md"
            tools_path.write_text(_safe_format(TEMPLATES["TOOLS.md"],
                agent_name=agent.get("name") or slug,
                slug=slug,
                worker_kind=agent.get("worker_kind") or "api",
                model_binding=agent.get("model_binding") or "unknown",
            ))

            # AGENTS.md
            agents_path = agent_dir / "AGENTS.md"
            agents_path.write_text(_safe_format(TEMPLATES["AGENTS.md"],
                agent_name=agent.get("name") or slug,
                slug=slug,
                company_id=agent.get("company_id") or "jarvis-war-room",
                team_id=agent.get("team_id") or "default",
                node_id=agent.get("node_id") or "hermes-local-0",
                reports_to_list=_format_bullets(edges["reports_to"]),
                manages_list=_format_bullets(edges["manages"]),
                collaborates_list=_format_bullets(edges["collaborates_with"]),
                team_mates_list=_format_bullets(team_mates),
            ))

            # Also record the paths in the agents row
            conn.execute(
                """UPDATE agents SET
                      heartbeat_path = ?, tools_path = ?, agents_path = ?
                   WHERE id = ?""",
                (str(hb_path), str(tools_path), str(agents_path), slug),
            )
            written.append(str(hb_path))
            written.append(str(tools_path))
            written.append(str(agents_path))

        # Audit
        conn.execute(
            """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
               VALUES (?, datetime('now'), 'jarvis-company-os', 'gen_agent_files',
                       'jarvis-war-room', ?)""",
            (str(uuid.uuid4()), json.dumps({"files_written": len(written)})),
        )
        conn.commit()
        return {
            "status": "generated",
            "agents": len(slugs),
            "files_written": len(written),
            "dir": str(AGENTS_HOME),
        }
    except Exception as e:
        conn.rollback()
        log.exception("gen_agent_files failed")
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(generate_all(), indent=2, default=str))
    sys.exit(0)
