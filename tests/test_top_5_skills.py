# Hermes Jarvis War Room — Tests for Top 5 Skills

## 1. Role-Based Agents

### `tests/test_role_based_agents.py`
```python
from fastapi.testclient import TestClient
from backend.api.agent_growth import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_assign_role():
    response = client.post("/agents/roles", json={"agent": "test-agent", "role": "Researcher"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_invalid_role():
    response = client.post("/agents/roles", json={"agent": "test-agent", "role": "InvalidRole"})
    assert response.status_code == 422
```

## 2. Dynamic Context Isolation

### `tests/test_context_isolation.py`
```python
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
```

## 3. Tool Marketplace

### `tests/test_marketplace.py`
```python
from fastapi.testclient import TestClient
from backend.api.marketplace import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_install_tool():
    response = client.post("/marketplace/install", json={"tool_name": "google_search"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_invalid_tool():
    response = client.post("/marketplace/install", json={"tool_name": "invalid_tool"})
    assert response.status_code == 422
```

## 4. Observability Dashboard

### `tests/test_observability.py`
```python
from backend.core.council import Council

def test_council_run_trace():
    council = Council()
    decision = council.run("Test query")
    assert decision.id is not None

def test_memory_operation_trace():
    from backend.core.memory_router import MemoryRouter
    router = MemoryRouter(project_id="test")
    item = router.add_fact("Test fact")
    assert item.id is not None
```

## 5. YAML Workflows

### `tests/test_workflows.py`
```python
from fastapi.testclient import TestClient
from backend.api.workflows import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_run_workflow():
    response = client.post("/workflows/run", json={"name": "research_to_report"})
    assert response.status_code == 200
    assert "status" in response.json()

def test_invalid_workflow():
    response = client.post("/workflows/run", json={"name": "invalid_workflow"})
    assert response.status_code == 422
```