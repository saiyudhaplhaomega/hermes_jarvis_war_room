"""Langfuse observability for War Room (D-2026-06-08-e, Phase E).

Per Loop 5 R2: Langfuse + OpenLLMetry/OTel as the default observability layer.
This module is a thin wrapper that:
  - Imports Langfuse lazily (won't fail if not installed)
  - Falls back to JSONL-on-disk if Langfuse server unreachable
  - Wraps every LLM call with trace + score + metadata

Usage:
    from core.observability import traced
    with traced("council-vote", metadata={"models": ["codex", "ollama:7b"]}):
        result = council.run(query)
"""
from __future__ import annotations
import os
import json
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Literal, Any


# Try to import langfuse. If missing, all operations are no-ops + JSONL.
try:
    from langfuse import Langfuse  # type: ignore
    _LANGFUSE_AVAILABLE = True
except Exception:
    _LANGFUSE_AVAILABLE = False


def _default_store_path() -> Path:
    return Path(os.environ.get(
        "JARVIS_DASHBOARD_OBS_DIR",
        str(Path.home() / ".hermes" / "state" / "observability"),
    ))


class Trace:
    """A single traced event. Mirrors Langfuse's trace shape so swapping
    backends is trivial (just change the import + write a parallel impl).
    """
    def __init__(self, name: str, trace_id: Optional[str] = None,
                 metadata: Optional[dict] = None):
        self.id = trace_id or str(uuid.uuid4())
        self.name = name
        self.start_ts = time.time()
        self.end_ts: Optional[float] = None
        self.metadata = metadata or {}
        self.events: list[dict] = []
        self.score: Optional[float] = None
        self.error: Optional[str] = None

    def event(self, name: str, payload: Optional[dict] = None) -> None:
        self.events.append({
            "name": name,
            "ts": time.time(),
            "payload": payload or {},
        })

    def set_score(self, score: float, comment: Optional[str] = None) -> None:
        """0.0 = bad, 1.0 = perfect. Optional human/automated feedback."""
        self.score = score
        if comment:
            self.metadata["score_comment"] = comment

    def set_error(self, error: Exception) -> None:
        self.error = f"{type(error).__name__}: {error}"

    def finish(self) -> None:
        if self.end_ts is None:
            self.end_ts = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "duration_ms": int((self.end_ts or time.time()) * 1000)
                          - int(self.start_ts * 1000),
            "metadata": self.metadata,
            "events": self.events,
            "score": self.score,
            "error": self.error,
        }


class ObservabilityClient:
    """Writes traces to Langfuse (if available) AND a JSONL fallback.

    The dual-write means:
      - Production gets the Langfuse UI for human inspection
      - Local dev / tests work without any external service
    """

    def __init__(self, store_path: Optional[Path] = None,
                 langfuse_host: Optional[str] = None,
                 langfuse_public_key: Optional[str] = None,
                 langfuse_secret_key: Optional[str] = None):
        self.store_path = Path(store_path or _default_store_path())
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.store_path / "traces.jsonl"
        self._langfuse = None
        if _LANGFUSE_AVAILABLE:
            try:
                self._langfuse = Langfuse(  # type: ignore
                    host=langfuse_host or os.environ.get("LANGFUSE_HOST"),
                    public_key=langfuse_public_key or os.environ.get("LANGFUSE_PUBLIC_KEY"),
                    secret_key=langfuse_secret_key or os.environ.get("LANGFUSE_SECRET_KEY"),
                )
            except Exception:
                # Auth missing or host unreachable; stay on JSONL
                self._langfuse = None

    def record(self, trace: Trace) -> None:
        """Write a finished trace. Always to JSONL; also to Langfuse if available."""
        trace.finish()
        # JSONL fallback (always)
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace.to_dict(), default=str) + "\n")
        # Langfuse (best effort)
        if self._langfuse is not None:
            try:
                # Translate to Langfuse's API; the `update` calls are
                # idempotent so a retry is safe.
                self._langfuse.trace(  # type: ignore
                    id=trace.id,
                    name=trace.name,
                    metadata=trace.metadata,
                )
                for ev in trace.events:
                    self._langfuse.event(  # type: ignore
                        trace_id=trace.id,
                        name=ev["name"],
                        metadata=ev["payload"],
                    )
                if trace.score is not None:
                    self._langfuse.score(  # type: ignore
                        trace_id=trace.id,
                        value=trace.score,
                        comment=trace.metadata.get("score_comment"),
                    )
            except Exception:
                # Don't fail the caller if Langfuse is down
                pass

    def list_recent(self, limit: int = 20) -> list[dict]:
        """Read recent traces from JSONL. Useful for the dashboard."""
        if not self.jsonl_path.exists():
            return []
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        rows = [json.loads(line) for line in lines if line.strip()]
        return rows[-limit:][::-1]  # newest first

    def stats(self) -> dict[str, Any]:
        traces = self.list_recent(limit=1000)
        scored = [t for t in traces if t.get("score") is not None]
        errored = [t for t in traces if t.get("error")]
        return {
            "total_traces": len(traces),
            "scored": len(scored),
            "errored": len(errored),
            "avg_score": (sum(t["score"] for t in scored) / len(scored)) if scored else None,
            "langfuse_enabled": self._langfuse is not None,
        }


# ─────────────────────────────────────────────
# Context manager
# ─────────────────────────────────────────────

# Global singleton so traces are aggregated in one place
_default_client: Optional[ObservabilityClient] = None


def get_client() -> ObservabilityClient:
    global _default_client
    if _default_client is None:
        _default_client = ObservabilityClient()
    return _default_client


@contextmanager
def traced(name: str, metadata: Optional[dict] = None,
           client: Optional[ObservabilityClient] = None):
    """Context manager: trace a block of code. Auto-records on exit.

    Usage:
        with traced("council-vote", metadata={"models": [...]}) as t:
            result = council.run(query)
            t.set_score(0.9)  # optional
            t.event("stage1_done", {"responses": 2})
    """
    c = client or get_client()
    t = Trace(name=name, metadata=metadata)
    try:
        yield t
    except Exception as e:
        t.set_error(e)
        raise
    finally:
        c.record(t)
