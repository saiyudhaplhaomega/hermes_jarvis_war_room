from backend.core.memory_router import MemoryRouter

def test_scope_filtering():
    router = MemoryRouter(project_id="test")
    router.add_fact("Test fact", context_scope="agent:test-agent")
    results = router.recall_facts("Test", context_scope="agent:test-agent")
    assert len(results) == 1

def test_global_scope():
    router = MemoryRouter(project_id="test")
    router.add_fact("Global fact", context_scope="global")
    results = router.recall_facts("Global", context_scope="global")
    assert len(results) == 1