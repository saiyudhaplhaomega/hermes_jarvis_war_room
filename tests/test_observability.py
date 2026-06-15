from backend.core.council import Council
from backend.core.memory_router import MemoryRouter

def test_council_run_trace():
    council = Council()
    decision = council.run("Test query")
    assert decision.id is not None

def test_memory_operation_trace():
    router = MemoryRouter(project_id="test")
    item = router.add_fact("Test fact")
    assert item.id is not None