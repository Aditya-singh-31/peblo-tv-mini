from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.security import get_current_user, get_db
from app.db.base import Base
from app.main import app
from app.models import Episode, Season, Show, User


@pytest.fixture
def validation_context(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'rules.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1,
        email="admin@example.com",
        username="admin",
        password_hash="unused",
        role="admin",
    )
    yield TestClient(app), session_factory, monkeypatch
    app.dependency_overrides.clear()


def test_incomplete_drafts_do_not_block_publication_report(validation_context) -> None:
    client, session_factory, _ = validation_context
    with session_factory() as session:
        show = Show(title="Draft show", status="draft")
        session.add(show)
        session.flush()
        season = Season(show_id=show.id, season_number=1, status="draft")
        session.add(season)
        session.flush()
        session.add(Episode(season_id=season.id, title="Draft episode", status="draft"))
        session.commit()

    response = client.get("/admin/validation-report")
    assert response.status_code == 200
    assert response.json()["can_publish"] is True
    assert response.json()["total_issues"] == 0


def test_invalid_reference_values_are_reported(validation_context) -> None:
    client, session_factory, monkeypatch = validation_context
    monkeypatch.setattr(
        "app.validation.report._reference_data",
        lambda: {"sections": ["featured"], "categories": ["education"], "languages": ["English"]},
    )
    with session_factory() as session:
        show = Show(title="Reference-invalid show", section="unknown", category="unknown", status="published")
        session.add(show)
        session.commit()

    response = client.get("/admin/validation-report")
    assert response.status_code == 200
    issues = response.json()["issues"]
    assert any(issue["field"] == "section" and "unsupported" in issue["problem"] for issue in issues)
    assert any(issue["field"] == "category" and "unsupported" in issue["problem"] for issue in issues)


def test_admin_can_publish_valid_content(validation_context, monkeypatch) -> None:
    client, session_factory, _ = validation_context
    monkeypatch.setattr("app.api.v1.catalog.catalogue_storage", __import__("app.storage.local", fromlist=["LocalStorage"]).LocalStorage())
    with session_factory() as session:
        show = Show(title="Admin publish show", section="featured", status="published")
        session.add(show)
        session.commit()

    response = client.post("/admin/catalog/publish")
    assert response.status_code == 200
    assert response.json()["outcome"] == "published"
