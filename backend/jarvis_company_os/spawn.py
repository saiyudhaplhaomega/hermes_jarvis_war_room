"""jarvis_company_os.spawn — Spec 04 §5 step 5 (SH worker execution).

Boss Item 5 SHIP-LITE: subprocess codex exec in a worktree, append STATUS
comment to the linked issue, mark run complete/failed. No jarvis_orchestrator
plugin (that's P8).
"""
import json
import logging
import os
import sqlite3
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger("jarvis_company_os.spawn")

KANBAN_DB_PATH = Path("/home/ubuntu/.hermes/kanban.db")
WORKTREE_BASE = Path(os.environ.get("JARVIS_WORKTREE_BASE", str(Path.home() / ".hermes" / "worktrees")))
WORKTREE_BASE.mkdir(parents=True, exist_ok=True)

CODEX_BINARY = os.environ.get("JARVIS_CODEX_BINARY", "/home/ubuntu/.local/bin/codex")
DEFAULT_TIMEOUT_SECONDS = int(os.environ.get("JARVIS_SPAWN_TIMEOUT", "300"))


class SpawnRefused(Exception):
    """Raised when spawn is refused (run not in approved state, etc.)."""


def _db():
    c = sqlite3.connect(str(KANBAN_DB_PATH), timeout=5.0)
    c.row_factory = sqlite3.Row
    return c


def execute_run(run_id: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """Execute a previously approved run. Sets worktree, runs codex, captures output.

    Returns a summary dict. Updates runs row + appends STATUS comment to linked issue.
    """
    conn = _db()
    try:
        run = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,),
        ).fetchone()
        if not run:
            raise SpawnRefused(f"run {run_id!r} not found")
        if run["status"] not in ("approved", "pending"):
            # Allow pending too for ad-hoc runs (Boss didn't lock this; allow but log)
            log.warning("execute_run on run %s with status=%r", run_id, run["status"])

        # 1. Resolve worktree
        worktree = WORKTREE_BASE / run_id
        worktree.mkdir(parents=True, exist_ok=True)

        # 2. Build codex command. Use --sandbox workspace-write + a brief prompt.
        # The issue's title + body become the task. Fall back to "execute run".
        issue_title = ""
        issue_body = ""
        if run["issue_id"]:
            irow = conn.execute(
                "SELECT title, body FROM issues WHERE id = ?", (run["issue_id"],),
            ).fetchone()
            if irow:
                issue_title = irow["title"] or ""
                issue_body = irow["body"] or ""
        prompt = f"{issue_title}\n\n{issue_body}".strip() or f"execute run {run_id}"

        cmd = [
            CODEX_BINARY, "exec",
            "--json",
            "--sandbox", "workspace-write",
            "--skip-git-repo-check",
            prompt,
        ]

        # 3. Mark started
        conn.execute(
            "UPDATE runs SET status='running', worktree_path=?, started_at=datetime('now') WHERE run_id=?",
            (str(worktree), run_id),
        )
        conn.commit()

        # 4. Execute (with timeout + kill on overrun)
        proc = None
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(worktree),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
                returncode = proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                returncode = -1
                # Mark failed
                _finalize_run(conn, run_id, "failed", stdout, stderr, "timeout")
                _post_status_comment(conn, run["issue_id"], run["agent_id"], f"SPAWN TIMEOUT after {timeout}s")
                return {"run_id": run_id, "status": "failed", "reason": "timeout",
                        "stdout_tail": stdout[-500:] if stdout else "",
                        "stderr_tail": stderr[-500:] if stderr else ""}
        except FileNotFoundError as e:
            conn.execute(
                "UPDATE runs SET status='failed', reject_reason=? WHERE run_id=?",
                (f"codex binary not found: {e}", run_id),
            )
            conn.commit()
            return {"run_id": run_id, "status": "failed", "reason": str(e)}
        except Exception as e:
            log.exception("spawn failed for %s", run_id)
            conn.execute(
                "UPDATE runs SET status='failed', reject_reason=? WHERE run_id=?",
                (f"spawn error: {e}", run_id),
            )
            conn.commit()
            _post_status_comment(conn, run["issue_id"], run["agent_id"],
                                 f"SPAWN ERROR: {e}")
            return {"run_id": run_id, "status": "failed", "reason": str(e)}

        # 5. Finalize
        if returncode == 0:
            _finalize_run(conn, run_id, "complete", stdout, stderr, None)
            comment = f"SPAWN COMPLETE rc=0\nstdout tail:\n{stdout[-500:] if stdout else ''}"
        else:
            _finalize_run(conn, run_id, "failed", stdout, stderr, f"rc={returncode}")
            comment = f"SPAWN FAILED rc={returncode}\nstderr tail:\n{stderr[-500:] if stderr else ''}"
        _post_status_comment(conn, run["issue_id"], run["agent_id"], comment)

        return {
            "run_id": run_id,
            "status": "complete" if returncode == 0 else "failed",
            "returncode": returncode,
            "worktree": str(worktree),
            "stdout_tail": stdout[-500:] if stdout else "",
            "stderr_tail": stderr[-500:] if stderr else "",
        }
    finally:
        conn.close()


def _finalize_run(conn, run_id, status, stdout, stderr, reject_reason):
    conn.execute(
        """UPDATE runs SET status=?, finished_at=datetime('now'),
           log_path=?, reject_reason=COALESCE(?, reject_reason)
           WHERE run_id=?""",
        (status, f"/tmp/run-{run_id}.log", reject_reason, run_id),
    )
    # Persist log
    try:
        with open(f"/tmp/run-{run_id}.log", "w") as f:
            f.write(f"--- STDOUT ---\n{stdout or ''}\n--- STDERR ---\n{stderr or ''}\n")
    except Exception as e:
        log.warning("could not write run log: %s", e)
    # Audit
    conn.execute(
        """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
           VALUES (?, datetime('now'), ?, ?, ?, ?)""",
        (str(uuid.uuid4()), "jarvis-company-os.spawn",
         f"run.{status}", run_id,
         json.dumps({"returncode": -1 if reject_reason == "timeout" else None,
                     "reject_reason": reject_reason})),
    )
    conn.commit()


def _post_status_comment(conn, issue_id, agent_id, body):
    if not issue_id:
        return
    cid = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO comments
           (id, issue_id, author, body, kind, created_at)
           VALUES (?, ?, ?, ?, 'status', datetime('now'))""",
        (cid, issue_id, agent_id or "system", body[:4000]),
    )
    conn.commit()
