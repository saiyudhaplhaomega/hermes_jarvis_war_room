from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def test_memory_trust_tier_schema_and_promotion_gate():
    from core.memory import MemoryItem, TrustTier, PromotionGate

    observed = MemoryItem(id="o1", content="x", tier=TrustTier.OBSERVED, observed_at=time.time(), last_used_at=time.time())
    inferred = MemoryItem(id="i1", content="y", tier=TrustTier.INFERRED, observed_at=time.time() - 60 * 60 * 24 * 30, last_used_at=time.time())
    cross_model = MemoryItem(id="c1", content="z", tier=TrustTier.CROSS_MODEL, observed_at=time.time(), last_used_at=time.time())

    gate = PromotionGate()
    assert gate.may_auto_apply(observed) is True
    assert gate.may_auto_apply(inferred) is False
    assert gate.may_auto_apply(cross_model) is False


def test_confidence_decay_reduces_inferred_and_preserves_user_stated():
    from core.memory import MemoryItem, TrustTier, ConfidenceDecay

    decay = ConfidenceDecay(half_life_seconds=60 * 60 * 24 * 7)
    inferred = MemoryItem(id="i1", content="x", tier=TrustTier.INFERRED, observed_at=time.time() - 60 * 60 * 24 * 30, last_used_at=time.time())
    user_stated = MemoryItem(id="u1", content="y", tier=TrustTier.USER_STATED, observed_at=time.time() - 60 * 60 * 24 * 30, last_used_at=time.time())

    assert decay.confidence(inferred) < 0.2
    assert decay.confidence(user_stated) >= 0.99


def test_activity_stream_redacts_tokens_and_reports_gaps():
    from core.activity import ActivityEvent, ActivityStream, REDACTED

    stream = ActivityStream()
    stream.append(ActivityEvent(t="agent.run", payload={"token": "super-secret", "msg": "ok"}))
    stream.append(ActivityEvent(t="deny", payload={"reason": "sse_token_url_rejected"}))
    stream.report_gap(duration_seconds=12)
    snapshot = stream.snapshot()
    assert snapshot["events"][0]["payload"]["token"] == REDACTED
    assert "super-secret" not in json.dumps(snapshot)
    assert snapshot["gaps"]


def test_context_recovery_uses_real_files_and_reports_fresh_project():
    from core.context_recovery import ContextRecovery

    recovery = ContextRecovery(repo_root=ROOT)
    summary = recovery.summarize()
    assert "files_indexed" in summary
    assert "decisions_indexed" in summary
    assert "specs_indexed" in summary
    # An empty docs/decisions tree without references must still report zero, not fabricated numbers.
    assert isinstance(summary["files_indexed"], int)
    assert isinstance(summary["decisions_indexed"], int)


def test_welcome_back_summary_cites_real_paths():
    from core.context_recovery import ContextRecovery

    recovery = ContextRecovery(repo_root=ROOT)
    summary = recovery.welcome_back()
    assert summary["recent_files"]
    for entry in summary["recent_files"]:
        assert Path(entry["path"]).exists()
