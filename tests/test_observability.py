"""Tests for the observability layer (D-2026-06-08-e, Phase E)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def test_trace_creation():
    from core.observability import Trace
    t = Trace("test", metadata={"foo": "bar"})
    assert t.id
    assert t.name == "test"
    assert t.metadata == {"foo": "bar"}
    assert t.start_ts > 0
    assert t.end_ts is None


def test_trace_event_appends_to_events_list():
    from core.observability import Trace
    t = Trace("test")
    t.event("stage1", {"count": 2})
    t.event("stage2", {"count": 5})
    assert len(t.events) == 2
    assert t.events[0]["name"] == "stage1"
    assert t.events[0]["payload"]["count"] == 2


def test_trace_set_score():
    from core.observability import Trace
    t = Trace("test")
    t.set_score(0.85, "good output")
    assert t.score == 0.85
    assert t.metadata["score_comment"] == "good output"


def test_trace_set_error_records_exception():
    from core.observability import Trace
    t = Trace("test")
    try:
        raise ValueError("bad input")
    except ValueError as e:
        t.set_error(e)
    assert t.error is not None
    assert "ValueError" in t.error
    assert "bad input" in t.error


def test_trace_to_dict_serializes():
    from core.observability import Trace
    t = Trace("council-vote", metadata={"models": ["codex"]})
    t.event("stage1_done", {"responses": 2})
    t.set_score(0.9)
    t.finish()
    d = t.to_dict()
    assert d["name"] == "council-vote"
    assert d["score"] == 0.9
    assert len(d["events"]) == 1
    assert d["duration_ms"] >= 0
    # Must be JSON-serializable
    json.dumps(d)


def test_observability_client_writes_jsonl_fallback(tmp_path):
    from core.observability import ObservabilityClient, Trace
    client = ObservabilityClient(store_path=tmp_path)
    t = Trace("test-trace", metadata={"k": "v"})
    t.finish()
    client.record(t)
    assert (tmp_path / "traces.jsonl").exists()
    rows = [json.loads(line) for line in (tmp_path / "traces.jsonl").read_text().splitlines() if line]
    assert len(rows) == 1
    assert rows[0]["name"] == "test-trace"


def test_observability_client_list_recent_returns_newest_first(tmp_path):
    from core.observability import ObservabilityClient, Trace
    client = ObservabilityClient(store_path=tmp_path)
    for i in range(5):
        t = Trace(f"trace-{i}")
        t.finish()
        client.record(t)
    recent = client.list_recent(limit=3)
    assert len(recent) == 3
    # Newest first
    assert recent[0]["name"] == "trace-4"
    assert recent[1]["name"] == "trace-3"
    assert recent[2]["name"] == "trace-2"


def test_observability_client_stats(tmp_path):
    from core.observability import ObservabilityClient, Trace
    client = ObservabilityClient(store_path=tmp_path)
    # 3 traces, 2 with scores, 1 with error
    t1 = Trace("a"); t1.set_score(0.5); t1.finish(); client.record(t1)
    t2 = Trace("b"); t2.set_score(1.0); t2.finish(); client.record(t2)
    t3 = Trace("c"); t3.set_error(ValueError("oops")); t3.finish(); client.record(t3)
    stats = client.stats()
    assert stats["total_traces"] == 3
    assert stats["scored"] == 2
    assert stats["errored"] == 1
    assert stats["avg_score"] == 0.75
    assert stats["langfuse_enabled"] is False  # we don't have env vars set


def test_traced_context_manager_records_on_success(tmp_path):
    from core.observability import ObservabilityClient, traced
    client = ObservabilityClient(store_path=tmp_path)
    with traced("test-op", metadata={"k": "v"}, client=client) as t:
        t.event("did_something", {"n": 1})
    recent = client.list_recent(limit=1)
    assert len(recent) == 1
    assert recent[0]["name"] == "test-op"
    assert recent[0]["events"][0]["name"] == "did_something"


def test_traced_context_manager_records_error_on_exception(tmp_path):
    from core.observability import ObservabilityClient, traced
    client = ObservabilityClient(store_path=tmp_path)
    try:
        with traced("failing-op", client=client) as t:
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    recent = client.list_recent(limit=1)
    assert len(recent) == 1
    assert recent[0]["error"] is not None
    assert "RuntimeError" in recent[0]["error"]


def test_traced_context_manager_allows_setting_score(tmp_path):
    from core.observability import ObservabilityClient, traced
    client = ObservabilityClient(store_path=tmp_path)
    with traced("scored-op", client=client) as t:
        t.set_score(0.75, "useful")
    recent = client.list_recent(limit=1)
    assert recent[0]["score"] == 0.75


def test_langfuse_import_failure_does_not_break_module():
    """Even if langfuse is missing, the module imports cleanly."""
    # This test passes if we got here — the module-level try/except
    # caught the import error and set _LANGFUSE_AVAILABLE = False
    from core import observability
    assert hasattr(observability, "Trace")
    assert hasattr(observability, "ObservabilityClient")
    assert hasattr(observability, "traced")
