"""Session transcript API — reads Hermes SQLite DB."""
import json, sqlite3
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from auth.dependencies import get_current_user

router = APIRouter(prefix="/sessions")

# Hermes session DB location (projected)
HERMES = Path.home() / ".hermes"
SESSION_DB = HERMES / "session.db"

# fallback: auto-discover any session DB

def _get_db() -> Path:
    if SESSION_DB.exists():
        return SESSION_DB
    for candidate in sorted((HERMES / "state").glob("*.db")):
        return candidate
    return SESSION_DB


@router.get("")
def list_sessions(limit: int = 20, offset: int = 0, user: str = Depends(get_current_user)):
    db = _get_db()
    if not db.exists():
        return {"sessions": [], "total": 0, "message": "No session database found"}
    try:
        conn = sqlite3.connect(str(db), timeout=2.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # attempt to find session metadata
        try:
            cur.execute("SELECT id, title, started_at, source FROM sessions ORDER BY started_at DESC LIMIT ? OFFSET ?", (limit, offset))
            rows = [dict(r) for r in cur.fetchall()]
        except Exception:
            return {"sessions": [], "total": 0, "message": "SESSIONS table not present"}
        total = 0
        try:
            cur.execute("SELECT COUNT(*) FROM sessions")
            total = cur.fetchone()[0]
        except Exception:
            pass
        conn.close()
        return {"sessions": rows, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB Error: {e}")


@router.get("/{session_id}")
def get_session_transcript(session_id: str, user: str = Depends(get_current_user)):
    db = _get_db()
    if not db.exists():
        raise HTTPException(status_code=404, detail="No session database")
    try:
        conn = sqlite3.connect(str(db), timeout=2.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute("SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at", (session_id,))
            rows = [dict(r) for r in cur.fetchall()]
        except Exception:
            return {"messages": [], "message": "MESSAGES table not present"}
        conn.close()
        return {"session_id": session_id, "messages": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB Error: {e}")
