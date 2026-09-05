from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.catalogue import PublishedCatalogue
from app.storage.local import LocalStorage


@pytest.fixture
def live_catalogue(tmp_path, monkeypatch) -> LocalStorage:
    storage = LocalStorage(root_dir=tmp_path / "catalogue", base_url="https://cdn.test")
    monkeypatch.setattr("app.api.v1.catalog.catalogue_storage", storage)
    catalogue = PublishedCatalogue.model_validate(
        {
            "schema_version": 1,
            "catalogue_version": "test-version",
            "featured_hero": {
                "show_id": "show-academy",
                "title": "Space Academy",
                "synopsis": "Learn beyond Earth.",
                "poster": "https://cdn.test/academy-poster.jpg",
                "banner": "https://cdn.test/academy-banner.jpg",
            },
            "sections": [
                {"key": "featured", "title": "Featured", "show_ids": ["show-academy"]},
                {"key": "archive", "title": "Archive", "show_ids": ["show-news"]},
            ],
            "categories": [
                {"key": "education", "title": "Education", "show_ids": ["show-academy"]},
                {"key": "news", "title": "News", "show_ids": ["show-news"]},
            ],
            "shows": [
                {
                    "id": "show-academy",
                    "title": "Space Academy",
                    "synopsis": "Learn beyond Earth.",
                    "categories": ["education"],
                    "poster": "https://cdn.test/academy-poster.jpg",
                    "banner": "https://cdn.test/academy-banner.jpg",
                    "thumbnail": None,
                    "seasons": [
                        {
                            "number": 1,
                            "title": "Season One",
                            "episodes": [
                                {
                                    "id": "episode-orbit",
                                    "title": "Orbit Basics",
                                    "synopsis": "A lesson about orbit.",
                                    "duration_seconds": 600,
                                    "thumbnail": "https://cdn.test/orbit.jpg",
                                    "languages": [{"code": "English"}, {"code": "Hindi"}],
                                },
                                {
                                    "id": "episode-math",
                                    "title": "Space Math",
                                    "synopsis": "Numbers in space.",
                                    "duration_seconds": 500,
                                    "thumbnail": None,
                                    "languages": [{"code": "English"}],
                                },
                            ],
                        }
                    ],
                },
                {
                    "id": "show-news",
                    "title": "Space News",
                    "synopsis": "Daily space reporting.",
                    "categories": ["news"],
                    "poster": None,
                    "banner": None,
                    "thumbnail": None,
                    "seasons": [
                        {
                            "number": 1,
                            "title": "Season One",
                            "episodes": [
                                {
                                    "id": "episode-mars",
                                    "title": "Mars Update",
                                    "synopsis": None,
                                    "duration_seconds": 300,
                                    "thumbnail": None,
                                    "languages": [{"code": "Hindi"}],
                                }
                            ],
                        }
                    ],
                },
            ],
        }
    )
    key = "catalogue/versions/test.json"
    storage.write_immutable(key, json.dumps(catalogue.model_dump(mode="json")).encode("utf-8"))
    storage.activate_pointer(key)
    return storage


def test_get_catalog_reads_only_live_catalogue(live_catalogue: LocalStorage) -> None:
    response = TestClient(app).get("/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert [show["id"] for show in payload["shows"]] == ["show-academy", "show-news"]
    assert "status" not in json.dumps(payload)
    assert "storage_key" not in json.dumps(payload)


def test_search_composes_query_and_filters_with_and_semantics(live_catalogue: LocalStorage) -> None:
    client = TestClient(app)

    response = client.get(
        "/catalog/search",
        params={
            "q": "space",
            "category": "education",
            "language": "Hindi",
            "section": "featured",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["show_id"] == "show-academy"
    assert [episode["id"] for episode in payload["items"][0]["episodes"]] == ["episode-orbit"]

    empty = client.get(
        "/catalog/search",
        params={
            "q": "space",
            "category": "education",
            "language": "Hindi",
            "section": "archive",
        },
    )
    assert empty.status_code == 200
    assert empty.json() == {"items": [], "total": 0}


def test_episode_title_and_category_search(live_catalogue: LocalStorage) -> None:
    client = TestClient(app)

    episode_match = client.get("/catalog/search", params={"q": "orbit"})
    assert episode_match.json()["total"] == 1
    assert episode_match.json()["items"][0]["episodes"][0]["title"] == "Orbit Basics"

    category_match = client.get("/catalog/search", params={"q": "education"})
    assert category_match.json()["total"] == 1
    assert category_match.json()["items"][0]["show_id"] == "show-academy"


def test_empty_catalogue_is_a_valid_viewer_result(tmp_path, monkeypatch) -> None:
    storage = LocalStorage(root_dir=tmp_path / "empty-catalogue")
    monkeypatch.setattr("app.api.v1.catalog.catalogue_storage", storage)

    client = TestClient(app)
    response = client.get("/catalog")
    assert response.status_code == 200
    assert response.json()["shows"] == []

    response = client.get("/catalog/search", params={"q": "anything"})

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}
