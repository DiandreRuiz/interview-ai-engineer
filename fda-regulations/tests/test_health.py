"""Health endpoint contract."""

from fastapi.testclient import TestClient


def test_health_ok_relaxed(client_relaxed: TestClient) -> None:
    response = client_relaxed.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["index_ready"] is False


def test_health_index_ready_when_manifest_present(client_with_index: TestClient) -> None:
    response = client_with_index.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["index_ready"] is True
