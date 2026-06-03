"""Kanban write actions (create, reclaim, reassign, block, unblock) with auth + audit + project scope."""
from fastapi import APIRouter, HTTPException, Depends, Query
import sqlite3
from datetime import datetime
from core.config import KANBAN_DB
from core.audit import log_action
from auth.dependencies import get_current_user

router = APIRouter()

def get_db():
    return sqlite3.connect(str(KANBAN_DB), timeout=5.0)

@router.post("/kanban/task")
def create_kanban_task(
    title: str,
    body: str = "",
    assignee: str = "jarvis-manager",
    priority: int = 1,
    project: str = "",
    parents: str = "",
    user: str = Depends(get_current_user)
):
    log_action(user, "write", "kanban.create", {"title": title, "assignee": assignee, "project": project})
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute("""
        INSERT INTO tasks (title, body, assignee, status, priority, project, last_heartbeat_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, body, assignee, "todo", priority, project, now, now, now))
    task_id = cur.lastrowid
    
    # Handle parent dependencies
    if parents:
        for p in parents.split(","):
            p = p.strip()
            if p:
                cur.execute("INSERT INTO task_deps (parent_id, child_id) VALUES (?, ?)", (p, f"t_{task_id}"))
    
    conn.commit()
    conn.close()
    return {"task_id": f"t_{task_id}", "status": "todo"}

@router.get("/kanban/tasks")
def list_tasks(
    project: str = Query(""),
    status: str = Query(""),
    assignee: str = Query(""),
    user: str = Depends(get_current_user)
):
    log_action(user, "read", "kanban.list", {"project": project})
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    where = ["t.status NOT IN ('archived', 'cancelled')"]
    params = []
    if project:
        where.append("t.project = ?")
        params.append(project)
    if status:
        where.append("t.status = ?")
        params.append(status)
    if assignee:
        where.append("t.assignee = ?")
        params.append(assignee)
    
    sql = f"""
        SELECT t.id, t.title, t.status, t.assignee, t.priority, t.project, t.last_heartbeat_at,
               t.body, t.created_at, t.updated_at,
               (SELECT GROUP_CONCAT(parent_id) FROM task_deps WHERE child_id = 't_' || t.id) as parents
        FROM tasks t
        WHERE {' AND '.join(where)}
        ORDER BY
          CASE t.status WHEN 'running' THEN 0 WHEN 'ready' THEN 1
                        WHEN 'blocked' THEN 2 WHEN 'todo' THEN 3 ELSE 4 END,
          t.priority DESC
    """
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    
    # Resolve parent status for each task
    for r in rows:
        r["id"] = f"t_{r['id']}"
        if r.get("parents"):
            parent_ids = r["parents"].split(",")
            # Check if any parent is not done
            placeholders = ",".join(["?"]*len(parent_ids))
            cur.execute(f"SELECT status FROM tasks WHERE 't_' || id IN ({placeholders})", parent_ids)
            parent_statuses = [s[0] for s in cur.fetchall()]
            r["blocked_by_parents"] = any(s != "done" for s in parent_statuses)
        else:
            r["blocked_by_parents"] = False
    
    conn.close()
    return {"tasks": rows, "count": len(rows)}

@router.post("/kanban/{task_id}/heartbeat")
def heartbeat_task(task_id: str, progress: str = "", user: str = Depends(get_current_user)):
    log_action(user, "write", "kanban.heartbeat", {"task_id": task_id, "progress": progress[:100]})
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute("UPDATE tasks SET last_heartbeat_at = ? WHERE id = ?", (now, task_id.replace("t_","")))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="task not found")
    conn.commit()
    conn.close()
    return {"ok": True, "heartbeat_at": now}

@router.post("/kanban/{task_id}/block")
def block_task(task_id: str, reason: str = "", user: str = Depends(get_current_user)):
    log_action(user, "write", "kanban.block", {"task_id": task_id, "reason": reason[:200]})
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status = 'blocked' WHERE id = ?", (task_id.replace("t_",""),))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="task not found")
    conn.commit()
    conn.close()
    return {"ok": True, "status": "blocked"}

@router.post("/kanban/{task_id}/unblock")
def unblock_task(task_id: str, user: str = Depends(get_current_user)):
    log_action(user, "write", "kanban.unblock", {"task_id": task_id})
    conn = get_db()
    cur = conn.cursor()
    tid = task_id.replace("t_","")
    # Check if blocked by parents
    cur.execute("SELECT parent_id FROM task_deps WHERE child_id = ?", (task_id,))
    parents = [r[0] for r in cur.fetchall()]
    if parents:
        placeholders = ",".join(["?"]*len(parents))
        cur.execute(f"SELECT status FROM tasks WHERE 't_' || id IN ({placeholders})", parents)
        parent_statuses = [s[0] for s in cur.fetchall()]
        if all(s == "done" for s in parent_statuses):
            new_status = "ready"
        else:
            new_status = "todo"
    else:
        new_status = "ready"
    cur.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, tid))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="task not found")
    conn.commit()
    conn.close()
    return {"ok": True, "status": new_status}

@router.post("/kanban/{task_id}/reclaim")
def reclaim_task(task_id: str, user: str = Depends(get_current_user)):
    log_action(user, "write", "kanban.reclaim", {"task_id": task_id})
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE tasks SET status = "ready" WHERE id=?', (task_id.replace("t_",""),))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="task not found")
    conn.commit()
    conn.close()
    return {"ok": True}

@router.post("/kanban/{task_id}/reassign")
def reassign_task(task_id: str, new_assignee: str, user: str = Depends(get_current_user)):
    log_action(user, "write", "kanban.reassign", {"task_id": task_id, "assignee": new_assignee})
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET assignee=? WHERE id=?", (new_assignee, task_id.replace("t_","")))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="task not found")
    conn.commit()
    conn.close()
    return {"ok": True}

@router.post("/kanban/{task_id}/complete")
def complete_task(task_id: str, summary: str = "", metadata: str = "", user: str = Depends(get_current_user)):
    log_action(user, "write", "kanban.complete", {"task_id": task_id})
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute("UPDATE tasks SET status = 'done', updated_at = ? WHERE id = ?", (now, task_id.replace("t_","")))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="task not found")
    # Check if any children should be unblocked
    cur.execute("SELECT child_id FROM task_deps WHERE parent_id = ?", (task_id,))
    children = [r[0] for r in cur.fetchall()]
    for child in children:
        child_tid = child.replace("t_","")
        # Check all parents of this child
        cur.execute("SELECT parent_id FROM task_deps WHERE child_id = ?", (child,))
        all_parents = [r[0] for r in cur.fetchall()]
        placeholders = ",".join(["?"]*len(all_parents)) if all_parents else "''"
        if all_parents:
            cur.execute(f"SELECT status FROM tasks WHERE 't_' || id IN ({placeholders})", all_parents)
            parent_statuses = [s[0] for s in cur.fetchall()]
            if all(s == "done" for s in parent_statuses):
                cur.execute("UPDATE tasks SET status = 'ready' WHERE id = ?", (child_tid,))
    conn.commit()
    conn.close()
    return {"ok": True, "status": "done", "children_unblocked": len(children)}

@router.get("/kanban/{task_id}")
def get_task(task_id: str, user: str = Depends(get_current_user)):
    log_action(user, "read", f"kanban.get/{task_id}")
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT t.*, 
               (SELECT GROUP_CONCAT(parent_id) FROM task_deps WHERE child_id = 't_' || t.id) as parents,
               (SELECT GROUP_CONCAT(child_id) FROM task_deps WHERE parent_id = 't_' || t.id) as children
        FROM tasks t WHERE t.id = ?
    """, (task_id.replace("t_",""),))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    r = dict(row)
    r["id"] = f"t_{r['id']}"
    return r

@router.get("/kanban/{task_id}/comments")
def get_comments(task_id: str, user: str = Depends(get_current_user)):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM task_comments WHERE task_id = ? ORDER BY created_at DESC", (task_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"comments": rows}

@router.post("/kanban/{task_id}/comment")
def add_comment(task_id: str, body: str = "", author: str = "", user: str = Depends(get_current_user)):
    log_action(user, "write", "kanban.comment", {"task_id": task_id})
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute("INSERT INTO task_comments (task_id, body, author, created_at) VALUES (?, ?, ?, ?)",
                (task_id, body, author or user, now))
    conn.commit()
    conn.close()
    return {"ok": True}

@router.get("/kanban/{task_id}/runs")
def get_runs(task_id: str, user: str = Depends(get_current_user)):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM task_runs WHERE task_id = ? ORDER BY started_at DESC", (task_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"runs": rows}
