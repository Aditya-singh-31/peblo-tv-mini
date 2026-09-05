from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CatalogueLanguage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)


class CatalogueEpisode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str
    synopsis: str | None
    duration_seconds: int | None
    thumbnail: str | None
    languages: list[CatalogueLanguage]


class CatalogueSeason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int = Field(gt=0)
    title: str | None
    episodes: list[CatalogueEpisode]


class CatalogueShow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str
    synopsis: str | None
    categories: list[str]
    poster: str | None
    banner: str | None
    thumbnail: str | None
    seasons: list[CatalogueSeason]


class CatalogueHero(BaseModel):
    model_config = ConfigDict(extra="forbid")

    show_id: str
    title: str
    synopsis: str | None
    poster: str | None
    banner: str | None


class CatalogueSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    title: str
    show_ids: list[str]


class CatalogueCategory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    title: str
    show_ids: list[str]


class PublishedCatalogue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    catalogue_version: str
    featured_hero: CatalogueHero | None
    sections: list[CatalogueSection]
    categories: list[CatalogueCategory]
    shows: list[CatalogueShow]


class CatalogueSearchEpisode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    synopsis: str | None
    duration_seconds: int | None
    thumbnail: str | None
    languages: list[CatalogueLanguage]
    season_number: int
    season_title: str | None


class CatalogueSearchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    show_id: str
    title: str
    synopsis: str | None
    categories: list[str]
    poster: str | None
    banner: str | None
    thumbnail: str | None
    episodes: list[CatalogueSearchEpisode]


class CatalogueSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CatalogueSearchItem]
    total: int
