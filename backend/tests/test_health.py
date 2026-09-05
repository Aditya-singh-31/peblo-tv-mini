from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class HealthyConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def execute(self, statement):
        return None


class HealthyEngine:
    def connect(self):
        return HealthyConnection()


class UnhealthyEngine:
    def connect(self):
        raise ConnectionError("database is unavailable")


def test_health_reports_service_and_postgresql_status_without_secrets(monkeypatch) -> None:
    monkeypatch.setattr("app.main.engine", HealthyEngine())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "peblo-api",
        "dependencies": {"postgresql": "ok"},
    }
    assert "password" not in response.text.lower()
    assert "secret" not in response.text.lower()
    assert "database_url" not in response.text.lower()


def test_health_returns_service_unavailable_when_postgresql_is_unreachable(monkeypatch) -> None:
    monkeypatch.setattr("app.main.engine", UnhealthyEngine())

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unhealthy",
        "service": "peblo-api",
        "dependencies": {"postgresql": "unavailable"},
    }
