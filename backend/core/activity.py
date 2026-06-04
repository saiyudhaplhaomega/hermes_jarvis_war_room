"""Privacy-filtered activity stream with gap detection."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


REDACTED = "[REDACTED]"

_SENSITIVE_KEYS = {"token", "authorization", "cookie", "password", "secret", "api_key"}
_TOKEN_LITERAL = re.compile(r"(?:Bearer\s+)?[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{8,}")


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k.lower() in _SENSITIVE_KEYS:
                out[k] = REDACTED
            else:
                out[k] = _scrub(v)
        return out
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if isinstance(value, str):
        return _TOKEN_LITERAL.sub(REDACTED, value)
    return value


@dataclass
class ActivityEvent:
    t: str
    payload: dict
    ts: float = 0.0

    def __post_init__(self) -> None:
        if not self.ts:
            import time
            self.ts = time.time()

    def to_dict(self) -> dict:
        return {"t": self.t, "payload": _scrub(self.payload), "ts": self.ts}


@dataclass
class ActivityStream:
    events: list[ActivityEvent] = field(default_factory=list)
    gaps: list[dict] = field(default_factory=list)
    max_events: int = 500

    def append(self, event: ActivityEvent) -> None:
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    def report_gap(self, *, duration_seconds: float, reason: str = "stream_gap") -> None:
        self.gaps.append({"duration_seconds": duration_seconds, "reason": reason})

    def snapshot(self) -> dict:
        return {
            "events": [e.to_dict() for e in self.events],
            "gaps": list(self.gaps),
        }
