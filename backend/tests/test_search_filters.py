from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage.local import LocalStorage


@pytest.fixture
def searchable_catalogue(tmp_path, monkeypatch) -> LocalStorage:
    storage = LocalStorage(root_dir=tmp_path / "catalogue")
    monkeypatch.setattr("app.api.v1.catalog.catalogue_storage", storage)
    payload = {
        "schema_version": 1,
        "catalogue_version": "search-test",
        "featured_hero": None,
        "sections": [
            {"key": "featured", "title": "Featured", "show_ids": ["show-space"]},
            {"key": "archive", "title": "Archive", "show_ids": ["show-news"]},
        ],
        "categories": [
            {"key": "education", "title": "Education", "show_ids": ["show-space"]},
            {"key": "news", "title": "News", "show_ids": ["show-news"]},
        ],
        "shows": [
            {
                "id": "show-space", "title": "Space Academy", "synopsis": "Learn", "categories": ["education"],
                "poster": None, "banner": None, "thumbnail": None,
                "seasons": [{"number": 1, "title": "One", "episodes": [{
                    "id": "ep-orbit", "title": "Orbit Lesson", "synopsis": None, "duration_seconds": 10,
                    "thumbnail": None, "languages": [{"code": "Hindi"}],
                }]}],
            },
            {
                "id": "show-news", "title": "Daily Brief", "synopsis": "News", "categories": ["news"],
                "poster": None, "banner": None, "thumbnail": None,
                "seasons": [{"number": 1, "title": "One", "episodes": [{
                    "id": "ep-space", "title": "Space Report", "synopsis": None, "duration_seconds": 10,
                    "thumbnail": None, "languages": [{"code": "English"}],
                }]}],
            },
        ],
    }
    key = "catalogue/versions/search.json"
    storage.write_immutable(key, json.dumps(payload).encode())
    storage.activate_pointer(key)
    return storage


def test_search_show_title(searchable_catalogue: LocalStorage) -> None:
    response = TestClient(app).get("/catalog/search?q=academy")
    assert [item["show_id"] for item in response.json()["items"]] == ["show-space"]


def test_search_episode_title(searchable_catalogue: LocalStorage) -> None:
    response = TestClient(app).get("/catalog/search?q=report")
    assert response.json()["items"][0]["episodes"][0]["id"] == "ep-space"


def test_search_category_and_filters(searchable_catalogue: LocalStorage) -> None:
    client = TestClient(app)
    assert client.get("/catalog/search", params={"category": "education"}).json()["total"] == 1
    assert client.get("/catalog/search", params={"language": "Hindi"}).json()["total"] == 1
    assert client.get("/catalog/search", params={"section": "archive"}).json()["total"] == 1
    combined = client.get("/catalog/search", params={"q": "space", "category": "education", "language": "Hindi", "section": "featured"})
    assert combined.json()["total"] == 1
    assert combined.json()["items"][0]["show_id"] == "show-space"
