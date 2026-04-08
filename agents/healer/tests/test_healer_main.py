from fastapi.testclient import TestClient

from healer.main import app


client = TestClient(app)


def test_service_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["healer"] == "online"
    assert data["status"] in {"healthy", "degraded"}
