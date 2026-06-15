"""Tests for structured fact store (c100-r12)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from core.fact_store import FactStore


def test_add_and_find_fact():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = FactStore(db_path=Path(db_path))
    fact = store.add_fact("Jarvis", "is_a", "company_os", "council", "engineering")
    assert fact.trust_score == 0.5
    found = store.find_fact(subject="Jarvis", namespace="engineering")
    assert len(found) == 1
    assert found[0].object == "company_os"


def test_trust_update():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = FactStore(db_path=Path(db_path))
    fact = store.add_fact("api", "status", "healthy", "monitor", "ops")
    updated = store.update_trust(int(fact.id), 1.0)
    assert updated is not None
    assert updated.trust_score > fact.trust_score


def test_search_facts_fts5():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = FactStore(db_path=Path(db_path))
    store.add_fact("Redis", "used_for", "caching sessions", "ops_doc", "ops")
    store.add_fact("Qdrant", "used_for", "vector search", "ops_doc", "ops")
    results = store.search_facts("vector", namespace="ops")
    assert any("Qdrant" in f.subject for f in results)


def test_consolidate_high_trust():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = FactStore(db_path=Path(db_path))
    f1 = store.add_fact("fact1", "is", "true", "src", "eng", initial_trust=0.9)
    f2 = store.add_fact("fact2", "is", "maybe", "src", "eng", initial_trust=0.5)
    consolidated = store.consolidate(namespace="eng", min_trust=0.8)
    subjects = {f.subject for f in consolidated}
    assert "fact1" in subjects
    assert "fact2" not in subjects
