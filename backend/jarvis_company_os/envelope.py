"""jarvis_company_os.envelope — spec 01 §4.3 Envelope schema + validation.

Used by /messages endpoint and the in-process bus shim. Every bus message
conforms to this shape. Artifacts are refs only, never blobs.
"""
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Spec 01 §4.3 — required fields. Optional fields may be omitted.
ENVELOPE_REQUIRED = {"id", "from", "to", "type", "priority", "created_at", "payload"}
ENVELOPE_OPTIONAL = {
    "conversation_id", "trace_id", "issue_id", "reply_to",
    "requires_ack", "artifacts", "task_state", "control_token",
    "deadline", "scheduled_at",
}

VALID_TYPES = {
    "TASK_ASSIGN", "TASK_ACCEPT", "TASK_REJECT",
    "STATUS", "RESULT",
    "QUERY", "REPLY",
    "REVIEW_REQUEST", "REVIEW_RESULT",
    "ESCALATION", "HANDOFF", "BROADCAST",
    "CONTRACT_PROPOSE", "CONTRACT_AGREE",
    "HIRE_REQUEST", "HIRE_RESULT",
    "WAKE", "LIVENESS", "CONTROL", "ACK", "ERROR",
}
VALID_PRIORITIES = {"low", "normal", "high", "urgent"}
VALID_TASK_STATES = {
    "submitted", "working", "input-required", "completed", "failed", "canceled",
}

# Agent URIs are hierarchical: org.<company>.<team>.<agent_id> or org.<co>.<team>.lead
URI_RE = re.compile(r"^org\.[a-z0-9-]+(\.[a-z0-9_-]+)+$|^org\.[a-z0-9-]+\.[a-z]+\.lead$|^org\.[a-z0-9-]+\.[a-z]+\.broadcast$")


class EnvelopeError(ValueError):
    """Raised on schema violation. Mapped to HTTP 400 by router."""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_envelope(
    from_uri: str,
    to_uri: str,
    type_: str,
    payload: Any,
    *,
    priority: str = "normal",
    issue_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    artifacts: Optional[List[Dict]] = None,
    task_state: Optional[str] = None,
    control_token: Optional[str] = None,
    requires_ack: bool = True,
) -> Dict[str, Any]:
    """Factory: build a valid envelope. Returns the dict (caller publishes it)."""
    env = {
        "id": str(uuid.uuid4()),
        "from": from_uri,
        "to": to_uri,
        "type": type_,
        "priority": priority,
        "payload": payload,
        "created_at": now_iso(),
        "requires_ack": requires_ack,
    }
    if issue_id:
        env["issue_id"] = issue_id
    if conversation_id:
        env["conversation_id"] = conversation_id
    else:
        env["conversation_id"] = str(uuid.uuid4())
    if trace_id:
        env["trace_id"] = trace_id
    else:
        env["trace_id"] = str(uuid.uuid4())
    if artifacts:
        env["artifacts"] = artifacts
    else:
        env["artifacts"] = []
    if task_state:
        env["task_state"] = task_state
    if control_token:
        env["control_token"] = control_token
    return env


def validate(env: Dict[str, Any]) -> None:
    """Raise EnvelopeError on any spec 01 §4.3 violation. No side effects."""
    if not isinstance(env, dict):
        raise EnvelopeError("envelope must be a JSON object")
    missing = ENVELOPE_REQUIRED - set(env.keys())
    if missing:
        raise EnvelopeError(f"missing required fields: {sorted(missing)}")
    extra = set(env.keys()) - (ENVELOPE_REQUIRED | ENVELOPE_OPTIONAL)
    if extra:
        raise EnvelopeError(f"unknown fields: {sorted(extra)}")
    if env["type"] not in VALID_TYPES:
        raise EnvelopeError(f"invalid type: {env['type']!r}")
    if env["priority"] not in VALID_PRIORITIES:
        raise EnvelopeError(f"invalid priority: {env['priority']!r}")
    if not URI_RE.match(env["from"]):
        raise EnvelopeError(f"invalid from URI: {env['from']!r}")
    if not URI_RE.match(env["to"]):
        raise EnvelopeError(f"invalid to URI: {env['to']!r}")
    if "task_state" in env and env["task_state"] not in VALID_TASK_STATES:
        raise EnvelopeError(f"invalid task_state: {env['task_state']!r}")
    if "artifacts" in env and not isinstance(env["artifacts"], list):
        raise EnvelopeError("artifacts must be a list")
    for art in env.get("artifacts", []):
        if not isinstance(art, dict) or "ref" not in art:
            raise EnvelopeError("each artifact needs at minimum 'ref'")
        if "kind" not in art:
            raise EnvelopeError("each artifact needs 'kind'")


def to_json(env: Dict[str, Any]) -> str:
    return json.dumps(env, default=str, ensure_ascii=False)
