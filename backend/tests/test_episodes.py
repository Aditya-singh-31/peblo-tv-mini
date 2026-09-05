from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.security import get_current_user, get_db
from app.db.base import Base
from app.main import app
from app.models import Artwork, User


@pytest.fixture
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'episodes.db'}")
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


def _create_season(client: TestClient, season_number: int = 1) -> tuple[int, int]:
    show = client.post("/admin/shows", json={"title": "Episode test show"})
    assert show.status_code == 201
    show_id = show.json()["id"]
    season = client.post(
        f"/admin/shows/{show_id}/seasons",
        json={"season_number": season_number},
    )
    assert season.status_code == 201
    return show_id, season.json()["id"]


def test_valid_episode_and_season_zero(client: TestClient) -> None:
    show_id, season_id = _create_season(client, season_number=0)

    response = client.post(
        "/admin/episodes",
        json={
            "season_id": season_id,
            "title": "Trailer episode",
            "content_group": "trailers",
            "language": "en",
        },
    )

    assert response.status_code == 201
    assert response.json()["season_id"] == season_id
    assert response.json()["season_number"] == 0
    assert response.json()["is_trailer"] is True
    filtered = client.get("/admin/episodes", params={"show_id": show_id, "season_id": season_id})
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1


def test_published_episode_reports_missing_duration_and_artwork(client: TestClient) -> None:
    _, season_id = _create_season(client)

    response = client.post(
        "/admin/episodes",
        json={"season_id": season_id, "title": "Ready episode", "status": "published"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["missing_fields"] == ["duration_seconds", "artwork"]


def test_published_episode_reports_missing_artwork(client: TestClient) -> None:
    _, season_id = _create_season(client)

    response = client.post(
        "/admin/episodes",
        json={
            "season_id": season_id,
            "title": "Needs artwork",
            "duration_seconds": 120,
            "status": "published",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["missing_fields"] == ["artwork"]


def test_episode_variants_uniqueness_publication_and_crud(client: TestClient, tmp_path) -> None:
    _, season_id = _create_season(client)
    first = client.post(
        "/admin/episodes",
        json={
            "season_id": season_id,
            "title": "English episode",
            "content_group": "episode-1",
            "language": "en",
        },
    )
    assert first.status_code == 201
    episode_id = first.json()["id"]

    duplicate = client.post(
        "/admin/episodes",
        json={
            "season_id": season_id,
            "title": "Duplicate English episode",
            "content_group": "episode-1",
            "language": "en",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["fields"] == ["content_group", "language"]

    french = client.post(
        "/admin/episodes",
        json={
            "season_id": season_id,
            "title": "French episode",
            "content_group": "episode-1",
            "language": "fr",
        },
    )
    assert french.status_code == 201

    engine = create_engine(f"sqlite:///{tmp_path / 'episodes.db'}")
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        session.add(
            Artwork(
                episode_id=episode_id,
                artwork_type="POSTER",
                storage_key="poster/episode-1.jpg",
            )
        )
        session.commit()

    published = client.patch(
        f"/admin/episodes/{episode_id}",
        json={"duration_seconds": 95, "status": "published"},
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["artwork_count"] == 1

    listed = client.get(
        "/admin/episodes",
        params={"search": "English", "status": "published", "language": "en", "page_size": 1},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert len(listed.json()["items"]) == 1

    fetched = client.get(f"/admin/episodes/{episode_id}")
    assert fetched.status_code == 200
    assert client.delete(f"/admin/episodes/{episode_id}").status_code == 204
    assert client.get(f"/admin/episodes/{episode_id}").status_code == 404
