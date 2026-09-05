from __future__ import annotations

import json
from pathlib import Path

from app.schemas.catalogue import PublishedCatalogue


CATALOGUE_PATH = Path(__file__).resolve().parents[3] / "challenge" / "example_catalogue.json"


def test_example_catalogue_matches_viewer_contract() -> None:
    catalogue = PublishedCatalogue.model_validate(json.loads(CATALOGUE_PATH.read_text(encoding="utf-8")))

    assert catalogue.schema_version == 1
    assert catalogue.featured_hero is None
    assert catalogue.sections == []
    assert catalogue.categories == []
    assert catalogue.shows == []


def test_catalogue_seasons_exclude_reserved_season_zero() -> None:
    catalogue = PublishedCatalogue.model_validate(
        {
            "schema_version": 1,
            "catalogue_version": "test",
            "featured_hero": None,
            "sections": [],
            "categories": [],
            "shows": [
                {
                    "id": "show-1",
                    "title": "Example",
                    "synopsis": None,
                    "categories": [],
                    "poster": None,
                    "banner": None,
                    "thumbnail": None,
                    "seasons": [
                        {
                            "number": 1,
                            "title": "Season One",
                            "episodes": [],
                        }
                    ],
                }
            ],
        }
    )

    assert all(season.number > 0 for show in catalogue.shows for season in show.seasons)
