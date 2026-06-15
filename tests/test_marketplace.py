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