"""Audit log API — reads ~/.hermes/state/audit/audit.jsonl."""
import json, os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from datetime import datetime
from auth.dependencies import get_current_user
import core.config as cfg

router = APIRouter(prefix="/audit")

HERMES = Path.home() / ".hermes"
AUDIT_FILE = HERMES / "state/audit/audit.jsonl"


def _redact(record: dict) -> dict:
    """Scrub secrets from audit record details before returning to client."""
    import copy, re
    rec = copy.deepcopy(record)
    details = rec.get("details", {})
    if not isinstance(details, dict):
        return rec
    for key in list(details.keys()):
        val = str(details[key])
        for pat in cfg.REDACTION_PATTERNS:
            if re.search(pat, val):
                details[key] = "[REDACTED]"
                break
    return rec
@router.get("")
def get_audit(
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    limit: int = 200,
    offset: int = 0,
    user: str = Depends(get_current_user),
):
    if not AUDIT_FILE.exists():
        return {"records": [], "total": 0, "message": "No audit log file found"}
    records = []
    try:
        with open(AUDIT_FILE, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line.strip())
                except Exception:
                    continue
                if severity and rec.get("severity") != severity:
                    continue
                if category and rec.get("category") != category:
                    continue
                if since:
                    try:
                        ts = datetime.fromisoformat(rec.get("ts", ""))
                        if ts.isoformat() < since:
                            continue
                    except Exception:
                        pass
                records.append(_redact(rec))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit read error: {e}")
    total = len(records)
    records = records[offset:offset+limit]
    return {"records": records, "total": total}


@router.get("/stream")
def audit_stream(user: str = Depends(get_current_user)):
    """Return the current number of audit lines for SSE poll."""
    if not AUDIT_FILE.exists():
        return {"lines": 0, "mtime": 0}
    mtime = os.path.getmtime(AUDIT_FILE)
    return {"lines": sum(1 for _ in open(AUDIT_FILE)), "mtime": mtime}
