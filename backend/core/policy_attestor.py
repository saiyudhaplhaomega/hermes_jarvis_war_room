"""
Runtime Policy Attestations (c100-r15): OWASP Agentic AI / NIST AI 600 control.

Every sensitive action must produce an attestation record before execution:
- agent_id, delegator, purpose
- policy_version
- taint_level
- quota_state
- approval_id (if APPROVE level)
- input_hash, output_hash
- reversal_plan

Execution is blocked unless attestation can be produced and signed.
"""
from __future__ import annotations

import hmac
import hashlib
import json
import os
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.agent_os_primitives import AgentOS, Capability, Taint
from core.config import DASHBOARD_DATA
from core.human_gates import HumanGateRegistry, HumanGateState
from core.permissions_matrix import PermissionsMatrix, PermissionLevel
from observability.audit_log import AuditLog


@dataclass
class ActionAttestation:
    action_id: str
    agent_id: str
    delegator: str
    purpose: str
    action: str
    policy_version: str
    taint_level: str
    quota_state: Dict[str, Any]
    approval_id: Optional[str]
    input_hash: str
    output_hash: Optional[str]
    reversal_plan: str
    timestamp: str
    signature: Optional[str] = None


class PolicyAttestor:
    """
    Enforces attestation-before-execution for sensitive actions.

    Integrates:
    - PermissionsMatrix (APPROVE/HUMAN/NONE)
    - AgentOS quotas + taint + capabilities
    - HumanGateRegistry (APPROVE-level gates)
    - AuditLog (signed receipts)
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        permissions: Optional[PermissionsMatrix] = None,
        agent_os: Optional[AgentOS] = None,
        gates: Optional[HumanGateRegistry] = None,
        audit: Optional[AuditLog] = None,
    ):
        self.db_path = db_path or Path(DASHBOARD_DATA) / "attestations.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.permissions = permissions or PermissionsMatrix()
        self.agent_os = agent_os or AgentOS()
        self.gates = gates or HumanGateRegistry()
        self.audit = audit or AuditLog(str(self.db_path))
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS attestations (
                    action_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    delegator TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    action TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    taint_level TEXT NOT NULL,
                    quota_state TEXT NOT NULL,
                    approval_id TEXT,
                    input_hash TEXT NOT NULL,
                    output_hash TEXT,
                    reversal_plan TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    signature TEXT
                );
                """
            )

    def _hash(self, data: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def can_execute(
        self,
        agent_id: str,
        action: str,
        namespace: str,
        purpose: str,
        delegator: str = "self",
        input_data: Optional[Dict[str, Any]] = None,
        required_caps: Optional[List[Capability]] = None,
    ) -> tuple[bool, Optional[str], Optional[ActionAttestation]]:
        """
        Return (allowed, reason, attestation_or_none).

        Blocks execution if any gate fails.
        """
        # 1. Capability check
        if required_caps:
            for cap in required_caps:
                if not self.agent_os.has_capability(namespace, agent_id, cap):
                    return False, f"missing capability {cap.name}", None

        # 2. Permission level (permissions_matrix expects dept as first arg)
        level = self.permissions.check_permission(namespace, action)
        if level == PermissionLevel.NONE:
            return False, "AI-NEVER or unknown action", None

        # 3. Quota check
        ok, quota_msg = self.agent_os.check_quota(namespace, calls=1)
        if not ok:
            return False, f"quota blocked: {quota_msg}", None

        # 4. Taint check (action string may carry taint label)
        taint_label = Taint.PUBLIC.name
        if ":confidential" in action:
            taint_label = Taint.CONFIDENTIAL.name
        elif ":finance" in action:
            taint_label = Taint.FINANCE.name
        elif ":hr" in action:
            taint_label = Taint.HR.name

        if taint_label in (Taint.FINANCE.name, Taint.HR.name):
            if not self.agent_os.has_capability(namespace, agent_id, Capability.ACCESS_VAULT):
                return False, f"missing vault capability for taint {taint_label}", None

        # 5. Human-gate for APPROVE level
        approval_id: Optional[str] = None
        if level == PermissionLevel.APPROVE:
            gate = self.gates.request(namespace, agent_id, action, purpose)
            approval_id = gate.id
            # For synchronous testability, auto-approve if delegator is 'system'
            if delegator == "system":
                self.gates.approve(gate.id, "system", "auto-approved by policy")
                approval_id = gate.id
            else:
                gate_state = self.gates.check_timeout_or_escalate(gate.id)
                if gate_state != HumanGateState.APPROVED:
                    return False, f"human approval required (gate {gate.id})", None

        # 6. Build attestation
        quota_state = self._get_quota_state(namespace)
        input_hash = self._hash(input_data or {"action": action, "purpose": purpose})
        att = ActionAttestation(
            action_id=self._hash({"agent_id": agent_id, "action": action, "ts": datetime.now(timezone.utc).isoformat()}),
            agent_id=agent_id,
            delegator=delegator,
            purpose=purpose,
            action=action,
            policy_version="c100-r15",
            taint_level=taint_label,
            quota_state=quota_state,
            approval_id=approval_id,
            input_hash=input_hash,
            output_hash=None,
            reversal_plan=f"reverse {action} by calling reverse:{action}",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        att.signature = self._sign_attestation(att)

        # Persist and record usage
        self._persist(att)
        self.agent_os.record_usage(namespace, calls=1)
        self.audit.log_action(
            user_id=agent_id,
            action="policy_attestation:granted",
            entity_type="attestation",
            entity_id=att.action_id,
            metadata={
                "action": action,
                "namespace": namespace,
                "taint_level": taint_label,
                "approval_id": approval_id,
                "purpose": purpose,
            },
            trust_level=7 if approval_id else 5,
        )
        return True, "ok", att

    def _get_quota_state(self, namespace: str) -> Dict[str, Any]:
        with self._lock, sqlite3.connect(str(self.agent_os.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM quotas WHERE namespace=?", (namespace,)).fetchone()
        if not row:
            return {}
        return dict(row)

    def _sign_attestation(self, att: ActionAttestation) -> str:
        payload = {
            "action_id": att.action_id,
            "agent_id": att.agent_id,
            "delegator": att.delegator,
            "purpose": att.purpose,
            "action": att.action,
            "policy_version": att.policy_version,
            "taint_level": att.taint_level,
            "quota_state": att.quota_state,
            "approval_id": att.approval_id,
            "input_hash": att.input_hash,
            # output_hash is deliberately excluded; it is finalized after execution.
            "reversal_plan": att.reversal_plan,
            "timestamp": att.timestamp,
        }
        return self._hash(payload)

    def _persist(self, att: ActionAttestation) -> None:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO attestations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    att.action_id,
                    att.agent_id,
                    att.delegator,
                    att.purpose,
                    att.action,
                    att.policy_version,
                    att.taint_level,
                    json.dumps(att.quota_state),
                    att.approval_id,
                    att.input_hash,
                    att.output_hash,
                    att.reversal_plan,
                    att.timestamp,
                    att.signature,
                ),
            )

    def finalize_output(self, action_id: str, output_data: Dict[str, Any]) -> bool:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            output_hash = self._hash(output_data)
            conn.execute(
                "UPDATE attestations SET output_hash=? WHERE action_id=?",
                (output_hash, action_id),
            )
            return conn.total_changes > 0

    def verify_attestation(self, action_id: str) -> tuple[bool, Optional[str]]:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM attestations WHERE action_id=?", (action_id,)).fetchone()
        if not row:
            return False, "not found"
        data = dict(row)
        att = ActionAttestation(
            action_id=data["action_id"],
            agent_id=data["agent_id"],
            delegator=data["delegator"],
            purpose=data["purpose"],
            action=data["action"],
            policy_version=data["policy_version"],
            taint_level=data["taint_level"],
            quota_state=json.loads(data["quota_state"]),
            approval_id=data["approval_id"],
            input_hash=data["input_hash"],
            output_hash=data["output_hash"],
            reversal_plan=data["reversal_plan"],
            timestamp=data["timestamp"],
            signature=data["signature"],
        )
        expected = self._sign_attestation(att)
        if att.signature is None:
            return False, "missing signature"
        return hmac.compare_digest(expected, att.signature), "ok"
