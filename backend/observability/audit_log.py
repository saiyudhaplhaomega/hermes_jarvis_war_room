"""
Audit Log (r55 + c100-r05): Append-only, hash-chained, signed receipts.

Each row includes:
- id, timestamp, user_id, action, entity_type, entity_id, metadata
- previous_hash (SHA-256 of prior row)
- row_hash (SHA-256 of this row's canonical content)
- trust_level (1-10, TRUST-1..TRUST-10)

Tamper detection: recompute row_hash and compare to stored value.
"""
import hashlib
import hmac
import json
import os
import sqlite3
from typing import Dict, List, Optional, Tuple


DEFAULT_SECRET = os.environ.get("JARVIS_AUDIT_HMAC_SECRET", "")


class AuditLog:
    def __init__(self, db_path: str = "kanban.db", hmac_secret: Optional[str] = None):
        self.db_path = db_path
        self.hmac_secret = (hmac_secret or DEFAULT_SECRET or "dev-only-secret").encode()
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    action TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id TEXT,
                    metadata TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    previous_hash TEXT,
                    row_hash TEXT,
                    trust_level INTEGER DEFAULT 1,
                    signature TEXT
                )
            """)
            conn.commit()

    def _canonical(self, row: Dict) -> str:
        """Stable canonical serialization for hashing, excluding id/timestamp/row_hash/signature."""
        safe = {
            k: v
            for k, v in row.items()
            if k not in ("id", "timestamp", "row_hash", "signature")
        }
        return json.dumps(safe, sort_keys=True, separators=(",", ":"))

    def _hash_row(self, row: Dict) -> str:
        return hashlib.sha256(self._canonical(row).encode()).hexdigest()

    def _last_hash(self) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else "0" * 64

    def _sign(self, row_hash: str) -> str:
        return hmac.new(self.hmac_secret, row_hash.encode(), hashlib.sha256).hexdigest()

    def log_action(
        self,
        user_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        metadata: Dict = None,
        trust_level: int = 1,
        ip_address: str = "",
        user_agent: str = "",
    ) -> bool:
        if not 1 <= trust_level <= 10:
            raise ValueError("trust_level must be 1..10")
        previous_hash = self._last_hash()
        row = {
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata": json.dumps(metadata) if metadata else None,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "previous_hash": previous_hash,
            "trust_level": trust_level,
        }
        row_hash = self._hash_row(row)
        signature = self._sign(row_hash)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_log
                (user_id, action, entity_type, entity_id, metadata,
                 ip_address, user_agent, previous_hash, row_hash, trust_level, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    action,
                    entity_type,
                    entity_id,
                    row["metadata"],
                    ip_address,
                    user_agent,
                    previous_hash,
                    row_hash,
                    trust_level,
                    signature,
                ),
            )
            conn.commit()
            return True

    def query_logs(self, filters: Dict = None) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM audit_log"
            if filters:
                conditions = " AND ".join([f"{k} = ?" for k in filters.keys()])
                query += f" WHERE {conditions}"
                cursor.execute(query, tuple(filters.values()))
            else:
                cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def verify_chain(self) -> Tuple[bool, List[Tuple[int, str]]]:
        """Return (ok, list of (id, reason)) for any tampered rows."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_log ORDER BY id")
            rows = [dict(row) for row in cursor.fetchall()]

        issues: List[Tuple[int, str]] = []
        prev_hash = "0" * 64
        for row in rows:
            stored_hash = row.pop("row_hash", None)
            stored_sig = row.pop("signature", None)
            expected_hash = self._hash_row(row)
            if expected_hash != stored_hash:
                issues.append((row["id"], "row hash mismatch"))
            elif not hmac.compare_digest(self._sign(expected_hash), stored_sig or ""):
                issues.append((row["id"], "signature mismatch"))
            elif row["previous_hash"] != prev_hash:
                issues.append((row["id"], "chain link broken"))
            prev_hash = stored_hash or expected_hash
        return len(issues) == 0, issues


if __name__ == "__main__":
    log = AuditLog()
    log.log_action("user1", "create_handoff", "handoff", "ticket123", trust_level=3)
    print("Audit Log initialized (r55 + c100-r05).")
    ok, issues = log.verify_chain()
    print(f"Chain verification: {ok}, issues: {issues}")
