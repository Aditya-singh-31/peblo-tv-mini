from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.security import get_current_user, get_db
from app.db.base import Base
from app.main import app
from app.models import User


@pytest.fixture
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'seasons.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1,
        email="editor@example.com",
        username="editor",
        password_hash="unused",
        role="editor",
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_show(client: TestClient) -> int:
    response = client.post("/admin/shows", json={"title": "Season test show"})
    assert response.status_code == 201
    return response.json()["id"]


def test_season_zero_is_allowed_and_marked_as_trailer(client: TestClient) -> None:
    show_id = _create_show(client)

    trailer = client.post(
        f"/admin/shows/{show_id}/seasons",
        json={"season_number": 0, "title": "Trailers"},
    )
    ordinary = client.post(
        f"/admin/shows/{show_id}/seasons",
        json={"season_number": 1, "title": "Season One"},
    )

    assert trailer.status_code == 201
    assert trailer.json()["is_trailer"] is True
    assert ordinary.status_code == 201
    assert ordinary.json()["is_trailer"] is False

    seasons = client.get(f"/admin/shows/{show_id}/seasons")
    assert seasons.status_code == 200
    assert [item["season_number"] for item in seasons.json()] == [0, 1]


def test_season_crud_and_validation(client: TestClient) -> None:
    show_id = _create_show(client)
    created = client.post(
        f"/admin/shows/{show_id}/seasons",
        json={"season_number": 1, "title": "Season One"},
    )
    season_id = created.json()["id"]

    duplicate = client.post(
        f"/admin/shows/{show_id}/seasons",
        json={"season_number": 1},
    )
    assert duplicate.status_code == 409

    invalid_number = client.post(
        f"/admin/shows/{show_id}/seasons",
        json={"season_number": -1},
    )
    assert invalid_number.status_code == 422

    invalid_status = client.post(
        f"/admin/shows/{show_id}/seasons",
        json={"season_number": 2, "status": "archived"},
    )
    assert invalid_status.status_code == 422

    updated = client.patch(
        f"/admin/seasons/{season_id}",
        json={"season_number": 2, "status": "published"},
    )
    assert updated.status_code == 200
    assert updated.json()["season_number"] == 2
    assert updated.json()["status"] == "published"

    fetched = client.get(f"/admin/seasons/{season_id}")
    assert fetched.status_code == 200
    assert fetched.json()["show_id"] == show_id

    assert client.delete(f"/admin/seasons/{season_id}").status_code == 204
    assert client.get(f"/admin/seasons/{season_id}").status_code == 404


def test_nested_season_create_requires_existing_show(client: TestClient) -> None:
    response = client.post("/admin/shows/999999/seasons", json={"season_number": 0})

    assert response.status_code == 404
    assert response.json()["detail"] == "Show not found"
