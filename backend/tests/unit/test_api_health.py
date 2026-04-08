from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """
    Verifies that the API is up and running and returns the correct status.
    """
    response = client.get("/health")
    assert response.status_code == 200
    # Check that the 'status' key exists and is 'ok', matching the actual API
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data

def test_root_endpoint():
    """
    Verifies the root endpoint accessibility and message.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to HyperCode Core API"}
