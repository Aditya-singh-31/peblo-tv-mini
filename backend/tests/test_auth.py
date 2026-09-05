from __future__ import annotations

from fastapi import status
from fastapi.testclient import TestClient

from app.auth.security import get_db, get_password_hash
from app.main import app
from app.models import User

client = TestClient(app)


def test_login_returns_token_for_valid_user() -> None:
    class FakeSession:
        def __init__(self):
            self.committed = False

        def execute(self, *args, **kwargs):
            class Result:
                @staticmethod
                def scalar_one_or_none():
                    return User(
                        id=1,
                        email="admin@example.com",
                        username="admin",
                        password_hash=get_password_hash("adminpass"),
                        role="admin",
                    )

            return Result()

        def close(self):
            return None

    def override_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = override_db

    try:
        response = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "adminpass"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert response.json()["role"] == "admin"


def test_login_rejects_invalid_credentials() -> None:
    class FakeSession:
        def execute(self, *args, **kwargs):
            class Result:
                @staticmethod
                def scalar_one_or_none():
                    return None

            return Result()

    def override_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = override_db
    try:
        response = client.post(
            "/auth/login",
            json={"email": "nope@example.com", "password": "wrong"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_current_user_requires_auth() -> None:
    response = client.get("/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
