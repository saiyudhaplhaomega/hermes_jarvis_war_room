"""jarvis_company_os.acl — spec 01 §4.6 authorize() + spec 04 audit_log.

Boss final ruling (D1, D2, D3) applied:
  6 rules instead of 5
  Rule 6 = request_budget_gate (D1) for TASK_ASSIGN
  CONTROL_gate uses HMAC JARVIS_CONTROL_TOKEN (D3) — not string URI
  7 test cases (D2) including explicit CONTROL deny + audit
"""
import hashlib
import hmac
import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("jarvis_company_os.acl")

KANBAN_DB_PATH = Path("/home/ubuntu/.hermes/kanban.db")

# ── JARVIS_CONTROL_TOKEN (Boss D3) ──────────────────────────────
# Generated at first deploy with `openssl rand -hex 32`, stored in env NEVER in DB.
# Control node signs CONTROL payloads with it; verify_control_token() is the gate.
ENV_VAR = "JARVIS_CONTROL_TOKEN"


def _load_control_token() -> bytes:
    tok = os.environ.get(ENV_VAR)
    if not tok:
        # Fail-closed: refuse to authorize any CONTROL message if token unset.
        log.warning("%s env var unset — CONTROL gate will deny all CONTROL messages", ENV_VAR)
        return b""
    return tok.encode("utf-8")


def sign_control_token(payload_nonce: str) -> str:
    """Control node calls this when emitting a CONTROL envelope."""
    secret = _load_control_token()
    if not secret:
        return ""
    mac = hmac.new(secret, payload_nonce.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def _hmac_for_envelope(env_id: str) -> str:
    secret = _load_control_token()
    if not secret:
        return ""
    return hmac.new(secret, env_id.encode("utf-8"), hashlib.sha256).hexdigest()


# ── AuthResult ───────────────────────────────────────────────────
@dataclass
class AuthResult:
    allowed: bool
    route: Optional[str] = None      # when denied, lead URI to escalate through
    reason: str = ""
    rule: str = ""                   # which of the 6 rules fired
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))


# ── DB helpers ───────────────────────────────────────────────────
def _db() -> sqlite3.Connection:
    c = sqlite3.connect(str(KANBAN_DB_PATH), timeout=5.0)
    c.row_factory = sqlite3.Row
    return c


def _agent_company_team(agent_id: str, conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    cur = conn.execute(
        "SELECT id, company_id, team_id, status FROM agents WHERE id = ?",
        (agent_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _edge_exists(frm: str, to: str, etype: str, conn: sqlite3.Connection) -> bool:
    cur = conn.execute(
        """SELECT 1 FROM edges
           WHERE type = ? AND from_agent = ? AND to_agent = ? LIMIT 1""",
        (etype, frm, to),
    )
    return cur.fetchone() is not None


def _lead_uri_for(agent_id: str, conn: sqlite3.Connection) -> Optional[str]:
    """Walk reports_to edges upward to find the manager (lead) of this agent."""
    cur = conn.execute(
        """SELECT to_agent FROM edges
           WHERE type = 'reports_to' AND from_agent = ? LIMIT 1""",
        (agent_id,),
    )
    row = cur.fetchone()
    return row["to_agent"] if row else None


def _write_audit(conn: sqlite3.Connection, actor: str, action: str,
                 target: str, detail: Dict[str, Any]) -> str:
    import json
    aid = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO audit_log (id, ts, actor, action, target, detail_json)
           VALUES (?, datetime('now'), ?, ?, ?, ?)""",
        (aid, actor, action, target, json.dumps(detail, default=str)),
    )
    return aid


# ── authorize() — the 6 rules (Boss D1) ────────────────────────
def authorize(env: Dict[str, Any]) -> AuthResult:
    """Pure(ish) authorization: envelope in, AuthResult out. No I/O on the bus.

    Rule order matters — first match wins.
    """
    from_uri = env["from"]
    to_uri = env["to"]
    msg_type = env["type"]
    env_id = env.get("id", str(uuid.uuid4()))

    # Extract agent ids from URIs (org.<co>.<team>.<agent_id>)
    from_agent = from_uri.rsplit(".", 1)[-1] if from_uri.startswith("org.") else from_uri
    to_agent = to_uri.rsplit(".", 1)[-1] if to_uri.startswith("org.") else to_uri

    conn = _db()
    try:
        from_info = _agent_company_team(from_agent, conn)
        to_info = _agent_company_team(to_agent, conn)

        # Rule 5: CONTROL_gate (Boss D3 — HMAC, not string URI)
        # Must fire BEFORE other rules because CONTROL bypasses all ACLs
        # when properly signed.
        if msg_type == "CONTROL":
            provided = env.get("control_token", "")
            if not provided or not _hmac_for_envelope(env_id) or \
               not hmac.compare_digest(provided, _hmac_for_envelope(env_id)):
                audit_id = _write_audit(conn, from_uri, "CONTROL_gate_deny", to_uri, {
                    "rule": 5, "env_id": env_id, "reason": "missing or invalid control_token",
                })
                conn.commit()
                return AuthResult(False, None, "CONTROL requires valid HMAC control_token",
                                  rule="5_control_gate", audit_id=audit_id)
            audit_id = _write_audit(conn, from_uri, "CONTROL_gate_allow", to_uri,
                                    {"rule": 5, "env_id": env_id})
            conn.commit()
            return AuthResult(True, reason="CONTROL signed", rule="5_control_gate",
                              audit_id=audit_id)

        # Unknown agents at endpoints — reject
        if not from_info or not to_info:
            audit_id = _write_audit(conn, from_uri, "auth_deny_unknown_agent", to_uri, {
                "from_known": bool(from_info), "to_known": bool(to_info),
            })
            conn.commit()
            return AuthResult(False, None, "unknown agent(s)", rule="unknown_agent",
                              audit_id=audit_id)

        # Cross-company never allowed
        if from_info["company_id"] != to_info["company_id"]:
            audit_id = _write_audit(conn, from_uri, "auth_deny_cross_company", to_uri, {
                "rule": "cross_company",
            })
            conn.commit()
            return AuthResult(False, None, "cross-company routing denied",
                              rule="cross_company", audit_id=audit_id)

        # Rule 1: vertical_down — reports_to from→to
        if _edge_exists(from_agent, to_agent, "reports_to", conn):
            audit_id = _write_audit(conn, from_uri, "auth_allow_vertical_down", to_uri,
                                    {"rule": 1})
            conn.commit()
            return AuthResult(True, reason="reports_to from→to", rule="1_vertical_down",
                              audit_id=audit_id)

        # Rule 2: vertical_up — reports_to to→from (escalation)
        if _edge_exists(to_agent, from_agent, "reports_to", conn):
            audit_id = _write_audit(conn, from_uri, "auth_allow_vertical_up", to_uri,
                                    {"rule": 2})
            conn.commit()
            return AuthResult(True, reason="escalation up", rule="2_vertical_up",
                              audit_id=audit_id)

        # Rule 3: horizontal — collaborates_with
        if _edge_exists(from_agent, to_agent, "collaborates_with", conn):
            audit_id = _write_audit(conn, from_uri, "auth_allow_horizontal", to_uri,
                                    {"rule": 3})
            conn.commit()
            return AuthResult(True, reason="collaborates_with", rule="3_horizontal",
                              audit_id=audit_id)

        # Rule 4: cross_team_no_edge — same company, different team, no edge
        # → DENY + route via from's lead
        if from_info["team_id"] != to_info["team_id"]:
            lead = _lead_uri_for(from_agent, conn)
            audit_id = _write_audit(conn, from_uri, "auth_deny_cross_team_route", to_uri, {
                "rule": 4, "via": lead,
            })
            conn.commit()
            return AuthResult(False, lead, "no edge, cross-team; route via lead",
                              rule="4_cross_team_no_edge", audit_id=audit_id)

        # Same team, no edge — also deny (spec 01 §4.6 default: no implicit peer)
        audit_id = _write_audit(conn, from_uri, "auth_deny_no_edge", to_uri, {
            "rule": "no_edge_same_team",
        })
        conn.commit()
        return AuthResult(False, None, "no edge; no implicit peer",
                          rule="no_edge_same_team", audit_id=audit_id)
    finally:
        conn.close()


def authorize_and_persist(env: Dict[str, Any]) -> AuthResult:
    """authorize() + on TASK_ASSIGN additionally check request budget (Rule 6)
    + persist to messages table on allow.

    Boss D1: rule 6 = request_budget_gate — closes the wake-cycle budget gap
    so Phase 3's emit_task_assign() is already gated without waiting for Phase 4.
    """
    result = authorize(env)

    # Rule 6: request_budget_gate (Boss D1) — only on TASK_ASSIGN and on allow
    if result.allowed and env["type"] == "TASK_ASSIGN":
        to_agent = env["to"].rsplit(".", 1)[-1]
        conn = _db()
        try:
            row = conn.execute(
                """SELECT requests_limit, requests_used FROM budgets
                   WHERE scope = 'agent' AND scope_id = ?""",
                (to_agent,),
            ).fetchone()
            if row and row["requests_limit"] is not None:
                if row["requests_used"] >= row["requests_limit"]:
                    audit_id = _write_audit(conn, env["from"], "request_budget_deny",
                                            env["to"], {
                        "rule": 6, "used": row["requests_used"],
                        "limit": row["requests_limit"],
                    })
                    conn.commit()
                    return AuthResult(False, None,
                                      f"agent {to_agent} at request budget cap "
                                      f"({row['requests_used']}/{row['requests_limit']})",
                                      rule="6_request_budget_gate", audit_id=audit_id)
        finally:
            conn.close()

    # Persist on allow (write messages row, increment budget)
    if result.allowed:
        import json
        conn = _db()
        try:
            conn.execute(
                """INSERT INTO messages
                   (id, conversation_id, trace_id, issue_id, from_uri, to_uri,
                    type, priority, payload_json, artifacts_json, task_state,
                    created_at, delivered, acked)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 1, 0)""",
                (
                    env["id"],
                    env.get("conversation_id"),
                    env.get("trace_id"),
                    env.get("issue_id"),
                    env["from"], env["to"],
                    env["type"],
                    {"low": 1, "normal": 5, "high": 8, "urgent": 10}.get(env["priority"], 5),
                    json.dumps(env.get("payload", {}), default=str),
                    json.dumps(env.get("artifacts", []), default=str),
                    env.get("task_state"),
                ),
            )
            if env["type"] == "TASK_ASSIGN":
                to_agent = env["to"].rsplit(".", 1)[-1]
                conn.execute(
                    """UPDATE budgets SET requests_used = COALESCE(requests_used,0) + 1
                       WHERE scope = 'agent' AND scope_id = ?""",
                    (to_agent,),
                )
            # On TASK_ASSIGN also append a status comment to the issue (spec 03 §1.2)
            if env["type"] == "TASK_ASSIGN" and env.get("issue_id"):
                conn.execute(
                    """INSERT INTO comments
                       (id, issue_id, author, body, kind, created_at)
                       VALUES (?, ?, ?, ?, 'status', datetime('now'))""",
                    (str(uuid.uuid4()), env["issue_id"], env["from"],
                     f"TASK_ASSIGN to {env['to']}", ),
                )
            conn.commit()
        finally:
            conn.close()
    return result
