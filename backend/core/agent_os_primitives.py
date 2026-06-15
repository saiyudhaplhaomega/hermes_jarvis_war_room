"""
Agent OS Primitives (c100-r03): capabilities, namespaces, quotas, taint,
audit, vault, outcomes. Modeled after kernel.chat/agent-os.

This module provides the low-level substrate that all department agents,
workflows, and tools run on top of.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.config import DASHBOARD_DATA


class Capability(Enum):
    """Fine-grained capabilities an agent/tool can hold."""
    READ_LEDGER = auto()
    WRITE_LEDGER = auto()
    READ_MEMORY = auto()
    WRITE_MEMORY = auto()
    SEND_DISCORD = auto()
    READ_DISCORD = auto()
    RUN_SHELL = auto()
    WRITE_FILE = auto()
    DEPLOY_PROD = auto()
    ACCESS_VAULT = auto()
    MANAGE_AGENTS = auto()
    VOTE_COUNCIL = auto()
    EXEC_WORKFLOW = auto()


class Taint(Enum):
    """Data taint labels for provenance tracking."""
    PUBLIC = auto()
    INTERNAL = auto()
    CONFIDENTIAL = auto()
    FINANCE = auto()
    HR = auto()
    EXTERNAL = auto()


@dataclass(frozen=True)
class Namespace:
    """A department/project isolation boundary."""
    name: str
    department: str = "*"
    project: str = "*"

    def __str__(self) -> str:
        return f"{self.department}/{self.project}/{self.name}"


@dataclass
class Quota:
    """Resource quota for a namespace or agent."""
    namespace: str
    max_calls_per_minute: int = 60
    max_tokens_per_hour: int = 1_000_000
    max_spend_per_day_usd: float = 50.0
    current_calls: int = 0
    current_tokens: int = 0
    current_spend_usd: float = 0.0


class AgentOS:
    """
    POSIX-like substrate for agents.

    Stores capabilities, namespaces, quotas, taint labels, audit events,
    vault secrets, and outcomes in a single SQLite database.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(DASHBOARD_DATA) / "agent_os.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS capabilities (
                    namespace TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    granted_at TEXT NOT NULL,
                    expires_at TEXT,
                    PRIMARY KEY (namespace, agent_id, capability)
                );
                CREATE TABLE IF NOT EXISTS namespaces (
                    name TEXT PRIMARY KEY,
                    department TEXT NOT NULL,
                    project TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS quotas (
                    namespace TEXT PRIMARY KEY,
                    max_calls_per_minute INTEGER NOT NULL,
                    max_tokens_per_hour INTEGER NOT NULL,
                    max_spend_per_day_usd REAL NOT NULL,
                    current_calls INTEGER NOT NULL DEFAULT 0,
                    current_tokens INTEGER NOT NULL DEFAULT 0,
                    current_spend_usd REAL NOT NULL DEFAULT 0.0,
                    reset_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS taint (
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    taint_label TEXT NOT NULL,
                    source_namespace TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    PRIMARY KEY (entity_type, entity_id, taint_label)
                );
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id TEXT,
                    metadata TEXT,
                    outcome TEXT
                );
                CREATE TABLE IF NOT EXISTS vault (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    taint_label TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    updated_by TEXT NOT NULL,
                    PRIMARY KEY (namespace, key)
                );
                CREATE TABLE IF NOT EXISTS outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    namespace TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    score REAL,
                    metadata TEXT,
                    recorded_at TEXT NOT NULL
                );
                """
            )

    # --- Capabilities ---

    def grant_capability(
        self,
        namespace: str,
        agent_id: str,
        capability: Capability,
        expires_at: Optional[str] = None,
    ) -> bool:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO capabilities VALUES (?, ?, ?, ?, ?)",
                    (
                        namespace,
                        agent_id,
                        capability.name,
                        datetime.now(timezone.utc).isoformat(),
                        expires_at,
                    ),
                )
                return True
            except sqlite3.Error:
                return False

    def revoke_capability(self, namespace: str, agent_id: str, capability: Capability) -> bool:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "DELETE FROM capabilities WHERE namespace=? AND agent_id=? AND capability=?",
                (namespace, agent_id, capability.name),
            )
            return conn.total_changes > 0

    def has_capability(self, namespace: str, agent_id: str, capability: Capability) -> bool:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT expires_at FROM capabilities WHERE namespace=? AND agent_id=? AND capability=?",
                (namespace, agent_id, capability.name),
            ).fetchone()
            if not row:
                return False
            expires = row[0]
            if expires and datetime.fromisoformat(expires) < datetime.now(timezone.utc):
                conn.execute(
                    "DELETE FROM capabilities WHERE namespace=? AND agent_id=? AND capability=?",
                    (namespace, agent_id, capability.name),
                )
                return False
            return True

    # --- Namespaces ---

    def create_namespace(self, name: str, department: str = "*", project: str = "*") -> bool:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            try:
                conn.execute(
                    "INSERT INTO namespaces VALUES (?, ?, ?, ?)",
                    (name, department, project, datetime.now(timezone.utc).isoformat()),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def list_namespaces(self, department: Optional[str] = None) -> List[Dict[str, str]]:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if department:
                rows = conn.execute(
                    "SELECT * FROM namespaces WHERE department=? OR department='*'", (department,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM namespaces").fetchall()
            return [dict(r) for r in rows]

    # --- Quotas ---

    def set_quota(
        self,
        namespace: str,
        max_calls_per_minute: int = 60,
        max_tokens_per_hour: int = 1_000_000,
        max_spend_per_day_usd: float = 50.0,
    ) -> bool:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO quotas
                       (namespace, max_calls_per_minute, max_tokens_per_hour,
                        max_spend_per_day_usd, reset_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        namespace,
                        max_calls_per_minute,
                        max_tokens_per_hour,
                        max_spend_per_day_usd,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                return True
            except sqlite3.Error:
                return False

    def check_quota(self, namespace: str, calls: int = 1, tokens: int = 0, spend_usd: float = 0.0) -> Tuple[bool, str]:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute("SELECT * FROM quotas WHERE namespace=?", (namespace,)).fetchone()
            if not row:
                return True, "no quota set"
            (
                _,
                max_calls,
                max_tokens,
                max_spend,
                current_calls,
                current_tokens,
                current_spend,
                reset_at,
            ) = row
            new_calls = current_calls + calls
            new_tokens = current_tokens + tokens
            new_spend = current_spend + spend_usd
            if new_calls > max_calls:
                return False, f"call quota exceeded ({new_calls}/{max_calls})"
            if new_tokens > max_tokens:
                return False, f"token quota exceeded ({new_tokens}/{max_tokens})"
            if new_spend > max_spend:
                return False, f"spend quota exceeded (${new_spend:.2f}/${max_spend:.2f})"
            return True, "ok"

    def record_usage(self, namespace: str, calls: int = 1, tokens: int = 0, spend_usd: float = 0.0) -> bool:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """UPDATE quotas SET
                   current_calls = current_calls + ?,
                   current_tokens = current_tokens + ?,
                   current_spend_usd = current_spend_usd + ?
                   WHERE namespace=?""",
                (calls, tokens, spend_usd, namespace),
            )
            return conn.total_changes > 0

    # --- Taint ---

    def apply_taint(
        self, entity_type: str, entity_id: str, taint: Taint, source_namespace: str
    ) -> bool:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO taint VALUES (?, ?, ?, ?, ?)",
                    (
                        entity_type,
                        entity_id,
                        taint.name,
                        source_namespace,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                return True
            except sqlite3.Error:
                return False

    def get_taint(self, entity_type: str, entity_id: str) -> List[str]:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute(
                "SELECT taint_label FROM taint WHERE entity_type=? AND entity_id=?",
                (entity_type, entity_id),
            ).fetchall()
            return [r[0] for r in rows]

    def can_read_with_taint(
        self, reader_caps: List[Capability], source_taint: List[Taint]
    ) -> bool:
        """Simplified taint check: FINANCE/HR require ACCESS_VAULT."""
        if Taint.FINANCE in source_taint or Taint.HR in source_taint:
            return Capability.ACCESS_VAULT in reader_caps
        return True

    # --- Audit ---

    def log_audit(
        self,
        namespace: str,
        agent_id: str,
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        outcome: Optional[str] = None,
    ) -> bool:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            try:
                conn.execute(
                    "INSERT INTO audit VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        datetime.now(timezone.utc).isoformat(),
                        namespace,
                        agent_id,
                        action,
                        entity_type,
                        entity_id,
                        json.dumps(metadata) if metadata else None,
                        outcome,
                    ),
                )
                return True
            except sqlite3.Error:
                return False

    def query_audit(self, namespace: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if namespace:
                rows = conn.execute(
                    "SELECT * FROM audit WHERE namespace=? ORDER BY timestamp DESC LIMIT ?",
                    (namespace, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM audit ORDER BY timestamp DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]

    # --- Vault ---

    def vault_write(
        self,
        namespace: str,
        key: str,
        value: str,
        taint_label: Taint,
        updated_by: str,
    ) -> bool:
        if not re.match(r"^[A-Za-z0-9_.-]{1,64}$", key):
            return False
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO vault VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        namespace,
                        key,
                        value,
                        taint_label.name,
                        datetime.now(timezone.utc).isoformat(),
                        updated_by,
                    ),
                )
                return True
            except sqlite3.Error:
                return False

    def vault_read(self, namespace: str, key: str, requester_caps: List[Capability]) -> Optional[str]:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT value, taint_label FROM vault WHERE namespace=? AND key=?",
                (namespace, key),
            ).fetchone()
            if not row:
                return None
            value, taint_name = row
            taint = Taint[taint_name]
            if not self.can_read_with_taint(requester_caps, [taint]):
                return None
            return value

    # --- Outcomes ---

    def record_outcome(
        self,
        namespace: str,
        agent_id: str,
        task_id: str,
        status: str,
        score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            try:
                conn.execute(
                    "INSERT INTO outcomes VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        namespace,
                        agent_id,
                        task_id,
                        status,
                        score,
                        json.dumps(metadata) if metadata else None,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                return True
            except sqlite3.Error:
                return False

    def get_outcomes(
        self, namespace: Optional[str] = None, agent_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM outcomes WHERE 1=1"
            params: List[Any] = []
            if namespace:
                query += " AND namespace=?"
                params.append(namespace)
            if agent_id:
                query += " AND agent_id=?"
                params.append(agent_id)
            query += " ORDER BY recorded_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]


__all__ = [
    "AgentOS",
    "Capability",
    "Namespace",
    "Quota",
    "Taint",
]
