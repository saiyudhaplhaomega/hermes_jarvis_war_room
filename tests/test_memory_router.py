"""Tests for the MemoryRouter (D-2026-06-08 memory M1)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def _make_router(tmp_path, project_id="warroom-test"):
    from core.memory_router import MemoryRouter
    return MemoryRouter(project_id=project_id, store_path=tmp_path)


def test_add_fact_writes_to_jsonl_fallback(tmp_path):
    r = _make_router(tmp_path)
    item = r.add_fact("Saiyudh prefers dark mode", trust_tier="USER_STATED")
    assert item.id
    assert item.data_type == "factual"
    assert item.content == "Saiyudh prefers dark mode"
    # JSONL fallback should have written a row
    log = tmp_path / "warroom-test" / "factual.jsonl"
    assert log.exists()
    rows = [json.loads(line) for line in log.read_text().splitlines() if line]
    assert len(rows) == 1
    assert rows[0]["content"] == "Saiyudh prefers dark mode"
    assert rows[0]["trust_tier"] == "USER_STATED"


def test_recall_facts_substring_match(tmp_path):
    r = _make_router(tmp_path)
    r.add_fact("Saiyudh prefers dark mode")
    r.add_fact("Saiyudh works at home")
    r.add_fact("Boss uses Codex")
    results = r.recall_facts("Saiyudh", limit=10)
    assert len(results) == 2
    # All results must contain "Saiyudh"
    for hit in results:
        assert "Saiyudh" in hit.content


def test_recall_facts_respects_limit(tmp_path):
    r = _make_router(tmp_path)
    for i in range(10):
        r.add_fact(f"Fact number {i}")
    results = r.recall_facts("Fact", limit=3)
    assert len(results) == 3


def test_add_state_writes_to_separate_log(tmp_path):
    r = _make_router(tmp_path)
    r.add_fact("a fact")
    r.add_state("a state-of-mind observation", agent_id="boss")
    stats = r.stats()
    assert stats["factual_count"] == 1
    assert stats["state_count"] == 1
    assert (tmp_path / "warroom-test" / "state.jsonl").exists()
    state_log = tmp_path / "warroom-test" / "state.jsonl"
    rows = [json.loads(line) for line in state_log.read_text().splitlines() if line]
    assert rows[0]["metadata"]["agent_id"] == "boss"


def test_recall_state_uses_state_log(tmp_path):
    r = _make_router(tmp_path)
    r.add_state("boss is thinking about topology editor")
    r.add_state("manager is thinking about memory strategy")
    results = r.recall_state("topology", limit=5)
    assert len(results) == 1
    assert "topology" in results[0].content


def test_stats_reflects_backend_availability(tmp_path):
    r = _make_router(tmp_path)
    stats = r.stats()
    assert "mem0_available" in stats
    assert "hindsight_available" in stats
    assert stats["project_id"] == "warroom-test"


def test_different_projects_have_isolated_storage(tmp_path):
    r1 = _make_router(tmp_path, project_id="project-a")
    r2 = _make_router(tmp_path, project_id="project-b")
    r1.add_fact("only in A")
    r2.add_fact("only in B")
    assert r1.recall_facts("only") != r2.recall_facts("only")
    assert (tmp_path / "project-a" / "factual.jsonl").exists()
    assert (tmp_path / "project-b" / "factual.jsonl").exists()
    assert not (tmp_path / "project-c").exists()
