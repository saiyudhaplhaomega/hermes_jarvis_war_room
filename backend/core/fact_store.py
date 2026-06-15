"""
Structured Fact Store (c100-r12): durable facts with trust scoring,
entity resolution, and automatic feedback loop.

Modeled after Memory OS Layer 3.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import DASHBOARD_DATA


@dataclass
class Fact:
    id: str
    subject: str
    predicate: str
    object: str
    trust_score: float
    source: str
    namespace: str
    created_at: datetime
    updated_at: datetime


class FactStore:
    """
    SQLite-backed structured facts with trust scoring.

    Trust score update rule (Bayesian-ish):
      new_trust = old_trust + alpha * (outcome_score - old_trust)
    where outcome_score is in [-1, 1].
    """

    def __init__(self, db_path: Optional[Path] = None, learning_rate: float = 0.2):
        self.db_path = db_path or Path(DASHBOARD_DATA) / "fact_store.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.alpha = learning_rate
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS fact_search USING fts5(
                    subject, predicate, object,
                    content='facts', content_rowid='id'
                );
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    trust_score REAL NOT NULL DEFAULT 0.5,
                    source TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
                    INSERT INTO fact_search(subject, predicate, object)
                    VALUES (new.subject, new.predicate, new.object);
                END;
                CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
                    INSERT INTO fact_search(fact_search, rowid, subject, predicate, object)
                    VALUES ('delete', old.id, old.subject, old.predicate, old.object);
                END;
                CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
                    INSERT INTO fact_search(fact_search, rowid, subject, predicate, object)
                    VALUES ('delete', old.id, old.subject, old.predicate, old.object);
                    INSERT INTO fact_search(subject, predicate, object)
                    VALUES (new.subject, new.predicate, new.object);
                END;
                """
            )

    def add_fact(
        self,
        subject: str,
        predicate: str,
        object: str,
        source: str,
        namespace: str = "default",
        initial_trust: float = 0.5,
    ) -> Fact:
        if not (0.0 <= initial_trust <= 1.0):
            raise ValueError("trust must be in [0,1]")
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                INSERT INTO facts
                (subject, predicate, object, trust_score, source, namespace, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (subject, predicate, object, initial_trust, source, namespace, now, now),
            )
            fact_id = cursor.lastrowid
            return self._to_fact({"id": fact_id, "subject": subject, "predicate": predicate,
                                  "object": object, "trust_score": initial_trust, "source": source,
                                  "namespace": namespace, "created_at": now, "updated_at": now})

    def _to_fact(self, data: Dict[str, Any]) -> Fact:
        return Fact(
            id=str(data["id"]),
            subject=data["subject"],
            predicate=data["predicate"],
            object=data["object"],
            trust_score=data["trust_score"],
            source=data["source"],
            namespace=data["namespace"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def find_fact(
        self, subject: Optional[str] = None, predicate: Optional[str] = None, namespace: Optional[str] = None
    ) -> List[Fact]:
        query = "SELECT * FROM facts WHERE 1=1"
        params: List[Any] = []
        if subject:
            query += " AND subject=?"
            params.append(subject)
        if predicate:
            query += " AND predicate=?"
            params.append(predicate)
        if namespace:
            query += " AND namespace=?"
            params.append(namespace)
        query += " ORDER BY trust_score DESC, updated_at DESC"
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [self._to_fact(dict(r)) for r in rows]

    def search_facts(self, q: str, namespace: Optional[str] = None, min_trust: float = 0.0) -> List[Fact]:
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            sql = """
                SELECT f.* FROM fact_search fs
                JOIN facts f ON f.id = fs.rowid
                WHERE fact_search MATCH ?
            """
            params: List[Any] = [f'"{q}"']
            if namespace:
                sql += " AND f.namespace=?"
                params.append(namespace)
            if min_trust > 0:
                sql += " AND f.trust_score >= ?"
                params.append(min_trust)
            sql += " ORDER BY f.trust_score DESC"
            rows = conn.execute(sql, params).fetchall()
        return [self._to_fact(dict(r)) for r in rows]

    def update_trust(self, fact_id: int, outcome_score: float) -> Optional[Fact]:
        if not (-1.0 <= outcome_score <= 1.0):
            raise ValueError("outcome_score must be in [-1,1]")
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM facts WHERE id=?", (fact_id,)).fetchone()
            if not row:
                return None
            data = dict(row)
            old_trust = data["trust_score"]
            new_trust = max(0.0, min(1.0, old_trust + self.alpha * (outcome_score - old_trust)))
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE facts SET trust_score=?, updated_at=? WHERE id=?",
                (new_trust, now, fact_id),
            )
            data["trust_score"] = new_trust
            data["updated_at"] = now
            return self._to_fact(data)

    def consolidate(self, namespace: Optional[str] = None, min_trust: float = 0.8) -> List[Fact]:
        """Return high-trust facts suitable for injection into agent prompts."""
        query = "SELECT * FROM facts WHERE trust_score >= ?"
        params: List[Any] = [min_trust]
        if namespace:
            query += " AND namespace=?"
            params.append(namespace)
        query += " ORDER BY trust_score DESC, updated_at DESC"
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [self._to_fact(dict(r)) for r in rows]


__all__ = ["FactStore", "Fact"]
