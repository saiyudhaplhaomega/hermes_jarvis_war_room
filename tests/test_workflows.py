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