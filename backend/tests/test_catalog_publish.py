from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.auth.security import get_current_user, get_db
from app.db.base import Base
from app.main import app
from app.models import Artwork, Episode, PublishRun, Season, Show, User
from app.storage.local import LocalStorage


@pytest.fixture
def publish_context(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'publish.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    storage = LocalStorage(root_dir=tmp_path / "catalogue", base_url="https://cdn.test")
    monkeypatch.setattr("app.api.v1.catalog.catalogue_storage", storage)

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    admin = User(id=1, email="admin@example.com", username="admin", password_hash="unused", role="admin")
    app.dependency_overrides[get_current_user] = lambda: admin
    with session_factory() as session:
        show = Show(
            title="Published Show",
            synopsis="Published synopsis",
            section="featured",
            category="stories",
            categories="Drama, Mystery",
            status="published",
        )
        draft_show = Show(
            title="Draft Show",
            synopsis="Not for viewers",
            section="series",
            status="draft",
        )
        session.add_all([show, draft_show])
        session.flush()
        trailer_season = Season(show_id=show.id, season_number=0, title="Trailers", status="published")
        season = Season(show_id=show.id, season_number=1, title="Season One", status="published")
        draft_season = Season(show_id=draft_show.id, season_number=1, title="Draft Season", status="draft")
        session.add_all([trailer_season, season, draft_season])
        session.flush()
        english = Episode(
            season_id=season.id,
            title="Episode One",
            synopsis="English synopsis",
            duration_seconds=120,
            language="en",
            content_group="episode-one",
            status="published",
        )
        french = Episode(
            season_id=season.id,
            title="Episode One",
            synopsis="French synopsis",
            duration_seconds=125,
            language="hi",
            content_group="episode-one",
            status="published",
        )
        trailer = Episode(
            season_id=trailer_season.id,
            title="Trailer",
            duration_seconds=30,
            language="en",
            content_group="trailer",
            status="published",
        )
        draft_episode = Episode(
            season_id=draft_season.id,
            title="Draft Episode",
            duration_seconds=60,
            language="en",
            content_group="draft-episode",
            status="draft",
        )
        session.add_all([english, french, trailer, draft_episode])
        session.flush()
        session.add_all(
            [
                Artwork(show_id=show.id, artwork_type="POSTER", storage_key="show/poster.jpg"),
                Artwork(show_id=show.id, artwork_type="BANNER", storage_key="show/banner.jpg"),
                Artwork(episode_id=english.id, artwork_type="THUMBNAIL", storage_key="episode/en.jpg"),
                Artwork(episode_id=french.id, artwork_type="THUMBNAIL", storage_key="episode/hi.jpg"),
                Artwork(episode_id=trailer.id, artwork_type="THUMBNAIL", storage_key="episode/trailer.jpg"),
                Artwork(episode_id=draft_episode.id, artwork_type="THUMBNAIL", storage_key="episode/draft.jpg"),
            ]
        )
        session.commit()

    yield session_factory, storage
    app.dependency_overrides.clear()


def test_publish_builds_filtered_grouped_catalogue_and_is_idempotent(publish_context) -> None:
    session_factory, storage = publish_context

    first = TestClient(app).post("/admin/catalog/publish")
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["show_count"] == 1
    assert first_payload["episode_count"] == 1
    assert storage.read_live_key() == first_payload["catalogue_key"]

    catalogue = json.loads(storage.read(first_payload["catalogue_key"]))
    assert catalogue["catalogue_version"] == first_payload["catalogue_version"]
    assert [show["title"] for show in catalogue["shows"]] == ["Published Show"]
    assert [season["number"] for season in catalogue["shows"][0]["seasons"]] == [1]
    episode = catalogue["shows"][0]["seasons"][0]["episodes"][0]
    assert episode["languages"] == [{"code": "en"}, {"code": "hi"}]
    assert episode["thumbnail"] == "https://cdn.test/episode/en.jpg"
    assert catalogue["shows"][0]["poster"] == "https://cdn.test/show/poster.jpg"
    assert catalogue["shows"][0]["banner"] == "https://cdn.test/show/banner.jpg"
    assert "status" not in json.dumps(catalogue)
    assert "storage_key" not in json.dumps(catalogue)

    second = TestClient(app).post("/admin/catalog/publish")
    assert second.status_code == 200
    assert second.json()["catalogue_version"] == first_payload["catalogue_version"]
    assert second.json()["catalogue_key"] == first_payload["catalogue_key"]

    with session_factory() as session:
        runs = session.execute(select(PublishRun).order_by(PublishRun.id)).scalars().all()
        assert [run.outcome for run in runs] == ["published", "published"]
        assert all(run.initiated_by_id == 1 for run in runs)


def test_validation_failure_does_not_change_live_catalogue(publish_context) -> None:
    session_factory, storage = publish_context
    client = TestClient(app)
    successful = client.post("/admin/catalog/publish")
    assert successful.status_code == 200
    old_key = storage.read_live_key()

    with session_factory() as session:
        episode = session.execute(select(Episode).where(Episode.title == "Episode One")).scalars().first()
        assert episode is not None
        episode.duration_seconds = None
        session.commit()

    failed = client.post("/admin/catalog/publish")
    assert failed.status_code == 422
    assert failed.json()["detail"]["outcome"] == "validation_failed"
    assert storage.read_live_key() == old_key
    with session_factory() as session:
        run = session.execute(select(PublishRun).order_by(PublishRun.id.desc())).scalars().first()
        assert run is not None
        assert run.outcome == "validation_failed"
        assert "duration_seconds" in (run.error_message or "")


def test_activation_failure_preserves_previous_live_catalogue(publish_context, monkeypatch) -> None:
    session_factory, storage = publish_context
    client = TestClient(app)
    successful = client.post("/admin/catalog/publish")
    assert successful.status_code == 200
    old_key = storage.read_live_key()

    def fail_activation(key: str, pointer_key: str = "catalogue/live.json") -> None:
        raise OSError("simulated pointer failure")

    monkeypatch.setattr(storage, "activate_pointer", fail_activation)
    failed = client.post("/admin/catalog/publish")

    assert failed.status_code == 500
    assert failed.json()["detail"]["outcome"] == "publish_failed"
    assert storage.read_live_key() == old_key
    with session_factory() as session:
        run = session.execute(select(PublishRun).order_by(PublishRun.id.desc())).scalars().first()
        assert run is not None
        assert run.outcome == "publish_failed"
        assert "simulated pointer failure" in (run.error_message or "")


def test_only_admins_can_publish(publish_context) -> None:
    app.dependency_overrides[get_current_user] = lambda: User(
        id=2,
        email="editor@example.com",
        username="editor",
        password_hash="unused",
        role="editor",
    )
    response = TestClient(app).post("/admin/catalog/publish")

    assert response.status_code == 403
