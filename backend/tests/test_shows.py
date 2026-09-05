from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth.security import get_current_user, get_db
from app.db.base import Base
from app.main import app
from app.models import Episode, Season, User


@pytest.fixture
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'shows.db'}")
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


def test_draft_can_be_created_without_section(client: TestClient) -> None:
    response = client.post("/admin/shows", json={"title": "Work in progress"})

    assert response.status_code == 201
    assert response.json()["section"] is None
    assert response.json()["status"] == "draft"


def test_published_show_requires_section(client: TestClient) -> None:
    response = client.post(
        "/admin/shows",
        json={"title": "Ready show", "status": "published"},
    )

    assert response.status_code == 422
    assert "section" in response.json()["detail"]["missing_fields"]


def test_show_crud_and_filters(client: TestClient, tmp_path) -> None:
    first = client.post(
        "/admin/shows",
        json={"title": "Nature Stories", "section": "featured"},
    ).json()
    second = client.post(
        "/admin/shows",
        json={"title": "City Stories", "section": "archive", "status": "published"},
    ).json()

    engine = create_engine(f"sqlite:///{tmp_path / 'shows.db'}")
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        season = Season(show_id=first["id"], season_number=1, status="draft")
        session.add(season)
        session.flush()
        session.add(Episode(season_id=season.id, title="Episode 1", language="en", status="draft"))
        session.commit()

    response = client.get("/admin/shows", params={"search": "Nature", "language": "en"})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == first["id"]

    paged = client.get("/admin/shows", params={"status": "published", "page": 1, "page_size": 1})
    assert paged.status_code == 200
    assert paged.json()["total"] == 1
    assert len(paged.json()["items"]) == 1

    updated = client.patch(
        f"/admin/shows/{first['id']}",
        json={"title": "Updated Nature Stories"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated Nature Stories"

    assert client.get(f"/admin/shows/{second['id']}").status_code == 200
    assert client.delete(f"/admin/shows/{second['id']}").status_code == 204
    assert client.get(f"/admin/shows/{second['id']}").status_code == 404
