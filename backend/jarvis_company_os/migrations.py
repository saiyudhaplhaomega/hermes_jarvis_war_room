"""jarvis_company_os.migrations — Apply spec 04 migrations to kanban.db.

Boss D-A (REVISED): target = /home/ubuntu/.hermes/kanban.db (same-db strategy).
Schema_migrations table tracks applied files; one row per filename.
Idempotent: safe to call from server.py lifespan on every restart.
"""
import sqlite3
import hashlib
import logging
from pathlib import Path
from typing import List, Tuple

log = logging.getLogger("jarvis_company_os.migrations")

# Where the migration SQL files live (per master plan §REPO LAYOUT)
MIGRATIONS_DIR = Path("/home/ubuntu/jarvis-war-room/migrations")

# The actual live kanban database (Boss D-A REVISED)
KANBAN_DB_PATH = Path("/home/ubuntu/.hermes/kanban.db")


def _ensure_schema_migrations(conn: sqlite3.Connection) -> None:
    """Create the tracking table if it doesn't exist (matches 001 idempotency)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
            filename    TEXT PRIMARY KEY,
            applied_at  TEXT NOT NULL DEFAULT (datetime('now')),
            checksum    TEXT
        )"""
    )
    conn.commit()


def _applied_set(conn: sqlite3.Connection) -> set:
    cur = conn.execute("SELECT filename FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def _file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def apply_pending() -> List[Tuple[str, str]]:
    """Apply any not-yet-applied migration files in MIGRATIONS_DIR.

    Returns list of (filename, status) for observability.
    Status is 'applied' or 'skipped' or 'error: <msg>'.
    """
    if not MIGRATIONS_DIR.exists():
        log.warning("migrations dir %s missing; nothing to apply", MIGRATIONS_DIR)
        return []
    if not KANBAN_DB_PATH.exists():
        log.warning("kanban.db at %s missing; cannot apply", KANBAN_DB_PATH)
        return []

    # Ensure parent dir exists (it should — kanban.db is at HERMES root)
    conn = sqlite3.connect(str(KANBAN_DB_PATH), timeout=5.0)
    try:
        _ensure_schema_migrations(conn)
        applied = _applied_set(conn)
        results: List[Tuple[str, str]] = []
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            fname = path.name
            if fname in applied:
                results.append((fname, "skipped"))
                continue
            try:
                sql = path.read_text()
                conn.executescript(sql)
                conn.execute(
                    "INSERT INTO schema_migrations (filename, checksum) VALUES (?, ?)",
                    (fname, _file_checksum(path)),
                )
                conn.commit()
                results.append((fname, "applied"))
                log.info("migration applied: %s", fname)
            except Exception as e:
                conn.rollback()
                results.append((fname, f"error: {e}"))
                log.exception("migration failed: %s", fname)
        return results
    finally:
        conn.close()
