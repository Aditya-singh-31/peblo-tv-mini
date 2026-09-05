from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.security import get_current_user, get_db
from app.db.base import Base
from app.main import app
from app.models import Artwork, Episode, Season, Show, User


@pytest.fixture
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'validation.db'}")
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
        yield test_client, session_factory
    app.dependency_overrides.clear()


def _create_show_with_season(client: TestClient, season_number: int) -> tuple[int, int]:
    show = client.post("/admin/shows", json={"title": "Example Show"})
    assert show.status_code == 201
    show_id = show.json()["id"]
    season = client.post(
        f"/admin/shows/{show_id}/seasons",
        json={"season_number": season_number, "title": "Trailers" if season_number == 0 else "Season One"},
    )
    assert season.status_code == 201
    return show_id, season.json()["id"]


def test_validation_report_discovers_imperfect_records(client) -> None:
    test_client, session_factory = client
    show_id, trailer_season_id = _create_show_with_season(test_client, 0)
    _, ordinary_season_id = _create_show_with_season(test_client, 1)

    first = test_client.post(
        "/admin/episodes",
        json={
            "season_id": ordinary_season_id,
            "title": "Episode 4",
            "content_group": "episode-4",
            "language": "en",
        },
    )
    second = test_client.post(
        "/admin/episodes",
        json={
            "season_id": ordinary_season_id,
            "title": "Episode 4 French",
            "content_group": "episode-4",
            "language": "fr",
        },
    )
    duplicate = test_client.post(
        "/admin/episodes",
        json={
            "season_id": ordinary_season_id,
            "title": "Episode 4 Duplicate",
            "content_group": "episode-4-duplicate",
            "language": "en",
        },
    )
    assert first.status_code == second.status_code == duplicate.status_code == 201

    with session_factory() as session:
        session.query(Show).update({"status": "published"})
        session.query(Season).update({"status": "published"})
        session.query(Episode).update({"status": "published"})
        session.add(
            Artwork(
                episode_id=duplicate.json()["id"],
                artwork_type="POSTER",
                storage_key="poster/invalid.jpg",
                width=600,
                height=600,
            )
        )
        session.commit()

    report = test_client.get("/admin/validation-report")

    assert report.status_code == 200
    payload = report.json()
    assert payload["can_publish"] is False
    assert payload["total_issues"] >= 7
    assert payload["groups"]["show"]
    assert payload["groups"]["season"] == []
    assert payload["groups"]["episode"]
    assert payload["groups"]["artwork"]

    problems = [issue["problem"] for issue in payload["issues"]]
    assert "Show 'Example Show' cannot be published because no section has been selected." in problems
    assert "Episode 'Episode 4' cannot be published because its duration is missing." in problems
    assert "Episode 'Episode 4' cannot be published because required artwork is missing." in problems
    assert any("invalid aspect ratio" in problem for problem in problems)
    assert all(issue["show_title"] for issue in payload["issues"])
    assert all(issue["suggested_fix"] for issue in payload["issues"])

    trailer_issues = [
        issue
        for issue in payload["issues"]
        if issue["entity_type"] == "season" and issue["entity_id"] == trailer_season_id
    ]
    assert trailer_issues == []
    assert show_id > 0
