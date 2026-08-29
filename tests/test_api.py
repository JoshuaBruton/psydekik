from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "healthy"
    assert body["service"] == "psydekik-api"
    assert "timestamp" in body


def test_get_system_status() -> None:
    response = client.get("/api/system/status")

    assert response.status_code == 200

    body = response.json()

    assert body["hostname"]
    assert body["uptime_seconds"] >= 0

    assert 0 <= body["cpu"]["usage_percent"] <= 100
    assert 0 <= body["memory"]["usage_percent"] <= 100
    assert 0 <= body["disk"]["usage_percent"] <= 100
