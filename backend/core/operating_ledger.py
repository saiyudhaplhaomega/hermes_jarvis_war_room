"""
Operating Ledger (r52): 10 entities, 6 pre-built views, read-only for dept tools.
"""
import json
import re
import sqlite3
from typing import Dict, List, Optional

# Allowlist of valid view names (prevents SQL injection).
ALLOWED_VIEWS = {
    "vw_accounts", "vw_contacts", "vw_deals",
    "vw_health_scores", "vw_renewals", "vw_mrr_trends",
}


class OperatingLedger:
    def __init__(self, db_path: str = "kanban.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ledger (
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (entity_type, entity_id)
                )
            """)
            # 6 pre-built views (r52)
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS vw_accounts AS
                SELECT entity_id, data FROM ledger WHERE entity_type = 'account'
            """)
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS vw_contacts AS
                SELECT entity_id, data FROM ledger WHERE entity_type = 'contact'
            """)
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS vw_deals AS
                SELECT entity_id, data FROM ledger WHERE entity_type = 'deal'
            """)
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS vw_health_scores AS
                SELECT entity_id, data FROM ledger WHERE entity_type = 'health_score'
            """)
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS vw_renewals AS
                SELECT entity_id, data FROM ledger WHERE entity_type = 'renewal'
            """)
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS vw_mrr_trends AS
                SELECT entity_id, data FROM ledger WHERE entity_type = 'mrr_trend'
            """)
            conn.commit()

    def write(self, entity_type: str, entity_id: str, data: Dict) -> bool:
        """Persist an entity to the ledger (JSON-encoded)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO ledger (entity_type, entity_id, data) VALUES (?, ?, ?)",
                (entity_type, entity_id, json.dumps(data))
            )
            conn.commit()
            return True

    def query(self, entity_type: str, entity_id: str) -> Optional[Dict]:
        """Query a single entity, returning parsed JSON dict."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data FROM ledger WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            try:
                return json.loads(row[0])
            except (json.JSONDecodeError, TypeError):
                return None

    def query_view(self, view_name: str, filters: Dict = None) -> List[Dict]:
        """Query a pre-built view, returning list of dicts (with parsed data)."""
        if view_name not in ALLOWED_VIEWS:
            raise ValueError(f"unknown view '{view_name}'. Allowed: {sorted(ALLOWED_VIEWS)}")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Whitelist filter keys to prevent SQL injection
            if filters:
                safe_filters = {k: v for k, v in filters.items() if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", k)}
                query = f"SELECT * FROM {view_name}"
                if safe_filters:
                    conditions = " AND ".join([f"{k} = ?" for k in safe_filters.keys()])
                    query += f" WHERE {conditions}"
                    cursor.execute(query, tuple(safe_filters.values()))
                else:
                    cursor.execute(query)
            else:
                cursor.execute(f"SELECT * FROM {view_name}")
            results = []
            for row in cursor.fetchall():
                # Row format: (entity_id, data_json_string)
                if len(row) >= 2:
                    entity_id = row[0]
                    try:
                        data = json.loads(row[1])
                    except (json.JSONDecodeError, TypeError):
                        data = row[1]  # Return raw string if not JSON
                    results.append({"entity_id": entity_id, "data": data})
                else:
                    results.append({"row": list(row)})
            return results


if __name__ == "__main__":
    ledger = OperatingLedger()
    print("Operating Ledger initialized (r52).")