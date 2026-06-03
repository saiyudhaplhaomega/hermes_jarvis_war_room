
"""Simple JSONL audit logger for compliance."""
import json, os
from datetime import datetime, timezone
from pathlib import Path
from core.config import AUDIT_LOG


def log_action(user: str, action: str, resource: str, details: dict = None):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": user,
        "action": action,
        "resource": resource,
        "details": details or {},
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
