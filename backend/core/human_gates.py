"""
Human-in-the-loop gating (c100-r07): APPROVE-level actions require human
approval before execution.

Integrates with:
- permissions_matrix.py (PermissionLevel.APPROVE)
- audit_log.py (signed receipts)
- AgentOS primitives (outcomes/audit)
"""
from __future__ import annotations

import re
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.config import DASHBOARD_DATA
from observability.audit_log import AuditLog


class HumanGateState(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    ESCALATED = "escalated"
    TIMEOUT = "timeout"


@dataclass
class HumanGatedAction:
    """A single human-gated action request."""

    dept: str
    agent_id: str
    action: str
    justification: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timeout_seconds: int = 3600
    escalation_after_seconds: int = 900
    state: HumanGateState = HumanGateState.PENDING
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    decision_reason: str = ""
    trust_level: int = 1


class HumanGateRegistry:
    """
    Persistent registry of human-gated actions.
    Stores actions in SQLite and emits signed audit receipts on state changes.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        audit_log: Optional[AuditLog] = None,
    ):
        self.db_path = db_path or Path(DASHBOARD_DATA) / "human_gates.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit = audit_log or AuditLog(str(self.db_path))
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS human_gates (
                    id TEXT PRIMARY KEY,
                    dept TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    justification TEXT,
                    state TEXT NOT NULL,
                    timeout_seconds INTEGER NOT NULL,
                    escalation_after_seconds INTEGER NOT NULL,
                    requested_at TEXT NOT NULL,
                    resolved_at TEXT,
                    resolved_by TEXT,
                    decision_reason TEXT,
                    trust_level INTEGER DEFAULT 1
                );
                """
            )

    def request(
        self,
        dept: str,
        agent_id: str,
        action: str,
        justification: str,
        timeout_seconds: int = 3600,
        escalation_after_seconds: int = 900,
    ) -> HumanGatedAction:
        if not re.match(r"^[A-Za-z0-9_.:/-]{1,128}$", action):
            raise ValueError("action contains invalid characters")
        gate = HumanGatedAction(
            dept=dept,
            agent_id=agent_id,
            action=action,
            justification=justification,
            timeout_seconds=timeout_seconds,
            escalation_after_seconds=escalation_after_seconds,
        )
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO human_gates
                (id, dept, agent_id, action, justification, state, timeout_seconds,
                 escalation_after_seconds, requested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    gate.id,
                    gate.dept,
                    gate.agent_id,
                    gate.action,
                    gate.justification,
                    gate.state.value,
                    gate.timeout_seconds,
                    gate.escalation_after_seconds,
                    gate.requested_at.isoformat(),
                ),
            )
        self._audit(gate, "requested")
        return gate

    def _load(self, gate_id: str) -> Optional[HumanGatedAction]:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM human_gates WHERE id=?", (gate_id,)
            ).fetchone()
        if not row:
            return None
        data = dict(row)
        return HumanGatedAction(
            id=data["id"],
            dept=data["dept"],
            agent_id=data["agent_id"],
            action=data["action"],
            justification=data["justification"] or "",
            state=HumanGateState(data["state"]),
            timeout_seconds=data["timeout_seconds"],
            escalation_after_seconds=data["escalation_after_seconds"],
            requested_at=datetime.fromisoformat(data["requested_at"]),
            resolved_at=datetime.fromisoformat(data["resolved_at"]) if data["resolved_at"] else None,
            resolved_by=data["resolved_by"],
            decision_reason=data["decision_reason"] or "",
            trust_level=data["trust_level"],
        )

    def _save(self, gate: HumanGatedAction) -> None:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                UPDATE human_gates SET
                  state=?,
                  resolved_at=?,
                  resolved_by=?,
                  decision_reason=?,
                  trust_level=?
                WHERE id=?
                """,
                (
                    gate.state.value,
                    gate.resolved_at.isoformat() if gate.resolved_at else None,
                    gate.resolved_by,
                    gate.decision_reason,
                    gate.trust_level,
                    gate.id,
                ),
            )

    def _audit(self, gate: HumanGatedAction, event: str) -> None:
        metadata = {
            "event": event,
            "gate_id": gate.id,
            "dept": gate.dept,
            "agent_id": gate.agent_id,
            "action": gate.action,
            "justification": gate.justification,
            "state": gate.state.value,
        }
        if gate.resolved_by:
            metadata["resolved_by"] = gate.resolved_by
            metadata["decision_reason"] = gate.decision_reason
        self.audit.log_action(
            user_id=gate.agent_id,
            action=f"human_gate:{event}",
            entity_type="human_gate",
            entity_id=gate.id,
            metadata=metadata,
            trust_level=gate.trust_level,
        )

    def approve(self, gate_id: str, human_id: str, reason: str = "") -> HumanGatedAction:
        gate = self._load(gate_id)
        if not gate:
            raise KeyError(f"gate {gate_id} not found")
        if gate.state not in (HumanGateState.PENDING, HumanGateState.ESCALATED):
            raise RuntimeError(f"cannot approve gate in state {gate.state.value}")
        gate.state = HumanGateState.APPROVED
        gate.resolved_by = human_id
        gate.decision_reason = reason
        gate.resolved_at = datetime.now(timezone.utc)
        gate.trust_level = 8
        self._save(gate)
        self._audit(gate, "approved")
        return gate

    def deny(self, gate_id: str, human_id: str, reason: str = "") -> HumanGatedAction:
        gate = self._load(gate_id)
        if not gate:
            raise KeyError(f"gate {gate_id} not found")
        if gate.state not in (HumanGateState.PENDING, HumanGateState.ESCALATED):
            raise RuntimeError(f"cannot deny gate in state {gate.state.value}")
        gate.state = HumanGateState.DENIED
        gate.resolved_by = human_id
        gate.decision_reason = reason
        gate.resolved_at = datetime.now(timezone.utc)
        gate.trust_level = 3
        self._save(gate)
        self._audit(gate, "denied")
        return gate

    def check_timeout_or_escalate(self, gate_id: str, now: Optional[datetime] = None) -> HumanGateState:
        gate = self._load(gate_id)
        if not gate:
            raise KeyError(f"gate {gate_id} not found")
        if gate.state not in (HumanGateState.PENDING, HumanGateState.ESCALATED):
            return gate.state
        now = now or datetime.now(timezone.utc)
        age = (now - gate.requested_at).total_seconds()
        if age >= gate.timeout_seconds:
            gate.state = HumanGateState.TIMEOUT
            gate.resolved_at = now
            self._save(gate)
            self._audit(gate, "timeout")
        elif age >= gate.escalation_after_seconds and gate.state == HumanGateState.PENDING:
            gate.state = HumanGateState.ESCALATED
            self._save(gate)
            self._audit(gate, "escalated")
        return gate.state

    def list_pending(self, dept: Optional[str] = None) -> List[HumanGatedAction]:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if dept:
                rows = conn.execute(
                    "SELECT * FROM human_gates WHERE state='pending' AND dept=?",
                    (dept,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM human_gates WHERE state='pending'").fetchall()
        return [self._load(dict(r)["id"]) for r in rows]


__all__ = ["HumanGatedAction", "HumanGateRegistry", "HumanGateState"]
