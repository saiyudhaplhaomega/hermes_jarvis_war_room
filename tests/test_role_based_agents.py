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