from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import Artwork, Episode, Season, Show
from app.storage.local import LocalStorage
from app.publishing.catalogue import build_catalogue


@pytest.fixture
def publish_context(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'determinism.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    storage = LocalStorage(root_dir=tmp_path / "catalogue", base_url="https://cdn.test")
    with session_factory() as session:
        show = Show(title="Published Show", section="featured", status="published")
        session.add(show)
        session.flush()
        season = Season(show_id=show.id, season_number=1, status="published")
        session.add(season)
        session.flush()
        episode = Episode(season_id=season.id, title="Episode", duration_seconds=10, language="en", content_group="episode", status="published")
        session.add(episode)
        session.flush()
        session.add(Artwork(episode_id=episode.id, artwork_type="THUMBNAIL", storage_key="episode/thumb.jpg"))
        session.commit()
    return session_factory, storage


def test_publish_ordering_is_deterministic(publish_context) -> None:
    session_factory, storage = publish_context
    with session_factory() as session:
        session.add_all([
            Show(title="Aardvark Show", section="series", status="published"),
            Show(title="Zebra Show", section="series", status="published"),
        ])
        session.commit()

    with session_factory() as session:
        first = build_catalogue(session, storage)
        second = build_catalogue(session, storage)

    assert first.data == second.data
    assert [show.title for show in first.catalogue.shows] == ["Aardvark Show", "Published Show", "Zebra Show"]
    assert first.version == second.version
    assert json.loads(first.data)["catalogue_version"] == first.version
