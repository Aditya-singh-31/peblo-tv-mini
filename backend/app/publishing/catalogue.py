from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Artwork, Episode, Season, Show
from app.schemas.catalogue import (
    CatalogueCategory,
    CatalogueEpisode,
    CatalogueHero,
    CatalogueLanguage,
    CatalogueSeason,
    CatalogueSection,
    CatalogueShow,
    PublishedCatalogue,
)
from app.storage.local import LocalStorage
from app.validation.report import build_validation_report


@dataclass(frozen=True)
class BuiltCatalogue:
    catalogue: PublishedCatalogue
    data: bytes
    version: str
    catalogue_key: str
    show_count: int
    episode_count: int


class CatalogueValidationError(ValueError):
    def __init__(self, report) -> None:
        self.report = report
        super().__init__(report.model_dump_json())


def _public_id(prefix: str, value: str | int) -> str:
    return f"{prefix}-{value}"


def _media_urls(artworks: Iterable[Artwork], storage: LocalStorage) -> dict[str, str]:
    selected: dict[str, Artwork] = {}
    for artwork in sorted(artworks, key=lambda item: (item.artwork_type.upper(), item.id)):
        selected.setdefault(artwork.artwork_type.upper(), artwork)
    return {
        key.lower(): storage.public_url(artwork.storage_key)
        for key, artwork in selected.items()
    }


def _show_categories(show: Show) -> list[str]:
    values: set[str] = set()
    if show.category and show.category.strip():
        values.add(show.category.strip())
    if show.categories:
        values.update(value.strip() for value in show.categories.split(",") if value.strip())
    return sorted(values, key=lambda value: (value.casefold(), value))


def _episode_group_key(episode: Episode) -> tuple[str, str]:
    if episode.content_group:
        return (str(episode.season_id), episode.content_group)
    return (str(episode.season_id), f"episode-{episode.id}")


def _group_episodes(episodes: Iterable[Episode], storage: LocalStorage) -> list[CatalogueEpisode]:
    grouped: dict[tuple[str, str], list[Episode]] = defaultdict(list)
    for episode in episodes:
        grouped[_episode_group_key(episode)].append(episode)

    result: list[CatalogueEpisode] = []
    for group_key, variants in grouped.items():
        ordered = sorted(
            variants,
            key=lambda item: (
                item.language is None,
                (item.language or "").casefold(),
                item.title.casefold(),
                item.id,
            ),
        )
        representative = ordered[0]
        language_codes = sorted(
            {episode.language for episode in variants if episode.language},
            key=lambda value: (value.casefold(), value),
        )
        media = _media_urls(
            [artwork for episode in variants for artwork in episode.artworks],
            storage,
        )
        public_id = _public_id("episode", group_key[1])
        result.append(
            CatalogueEpisode(
                id=public_id,
                title=representative.title,
                synopsis=representative.synopsis,
                duration_seconds=representative.duration_seconds,
                thumbnail=media.get("thumbnail"),
                languages=[CatalogueLanguage(code=code) for code in language_codes],
            )
        )
    return sorted(result, key=lambda episode: (episode.title.casefold(), episode.id))


def _build_show(
    show: Show,
    published_episodes: Iterable[Episode],
    show_artworks: Iterable[Artwork],
    storage: LocalStorage,
) -> CatalogueShow:
    episodes_by_season: dict[int, list[Episode]] = defaultdict(list)
    for episode in published_episodes:
        episodes_by_season[episode.season_id].append(episode)

    seasons: list[CatalogueSeason] = []
    for season in sorted(show.seasons, key=lambda item: (item.season_number, item.id)):
        if season.season_number == 0:
            continue
        episodes = _group_episodes(episodes_by_season.get(season.id, []), storage)
        if not episodes:
            continue
        seasons.append(
            CatalogueSeason(
                number=season.season_number,
                title=season.title,
                episodes=episodes,
            )
        )

    media = _media_urls(show_artworks, storage)
    return CatalogueShow(
        id=_public_id("show", show.id),
        title=show.title,
        synopsis=show.synopsis,
        categories=_show_categories(show),
        poster=media.get("poster"),
        banner=media.get("banner"),
        thumbnail=media.get("thumbnail"),
        seasons=seasons,
    )

def _canonical_bytes(catalogue: PublishedCatalogue) -> bytes:
    return json.dumps(
        catalogue.model_dump(mode="json"),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_catalogue(db: Session, storage: LocalStorage) -> BuiltCatalogue:
    report = build_validation_report(db)
    if not report.can_publish:
        raise CatalogueValidationError(report)

    shows = db.execute(
        select(Show)
        .options(selectinload(Show.seasons).selectinload(Season.episodes).selectinload(Episode.artworks))
        .order_by(Show.title, Show.id)
        .where(Show.status == "published")
    ).scalars().all()
    episodes = db.execute(
        select(Episode)
        .options(selectinload(Episode.artworks), selectinload(Episode.season))
        .join(Season)
        .where(Episode.status == "published")
        .order_by(Episode.id)
    ).scalars().all()
    show_artwork_rows = db.execute(
        select(Artwork).where(Artwork.show_id.is_not(None), Artwork.episode_id.is_(None)).order_by(Artwork.id)
    ).scalars().all()
    show_artworks_by_id: dict[int, list[Artwork]] = defaultdict(list)
    for artwork in show_artwork_rows:
        if artwork.show_id is not None:
            show_artworks_by_id[artwork.show_id].append(artwork)

    episodes_by_season: dict[int, list[Episode]] = defaultdict(list)
    for episode in episodes:
        episodes_by_season[episode.season_id].append(episode)

    public_shows: list[CatalogueShow] = []
    public_show_sources: dict[str, Show] = {}
    for show in shows:
        public_show = _build_show(
            show,
            episodes_by_show_season(show, episodes_by_season),
            show_artworks_by_id.get(show.id, []),
            storage,
        )
        public_shows.append(public_show)
        public_show_sources[public_show.id] = show
    public_shows.sort(key=lambda show: (show.title.casefold(), show.id))

    show_by_id = {show.id: show for show in public_shows}
    section_ids: dict[str, list[str]] = defaultdict(list)
    category_ids: dict[str, list[str]] = defaultdict(list)
    for public_show in public_shows:
        source_show = public_show_sources[public_show.id]
        if source_show.section:
            section_ids[source_show.section].append(public_show.id)
        for category in public_show.categories:
            category_ids[category].append(public_show.id)

    sections = [
        CatalogueSection(
            key=key,
            title=key,
            show_ids=sorted(ids),
        )
        for key, ids in sorted(section_ids.items(), key=lambda item: (item[0].casefold(), item[0]))
    ]
    categories = [
        CatalogueCategory(
            key=key,
            title=key,
            show_ids=sorted(ids),
        )
        for key, ids in sorted(category_ids.items(), key=lambda item: (item[0].casefold(), item[0]))
    ]
    hero_source = None
    featured = next((section for section in sections if section.key.casefold() == "featured" and section.show_ids), None)
    if featured:
        hero_source = show_by_id[sorted(featured.show_ids)[0]]
    elif public_shows:
        hero_source = public_shows[0]
    hero = (
        CatalogueHero(
            show_id=hero_source.id,
            title=hero_source.title,
            synopsis=hero_source.synopsis,
            poster=hero_source.poster,
            banner=hero_source.banner,
        )
        if hero_source
        else None
    )

    base_catalogue = PublishedCatalogue(
        catalogue_version="",
        featured_hero=hero,
        sections=sections,
        categories=categories,
        shows=public_shows,
    )
    digest = hashlib.sha256(_canonical_bytes(base_catalogue)).hexdigest()
    catalogue = base_catalogue.model_copy(update={"catalogue_version": f"sha256:{digest}"})
    data = _canonical_bytes(catalogue) + b"\n"
    PublishedCatalogue.model_validate_json(data)
    version = catalogue.catalogue_version
    return BuiltCatalogue(
        catalogue=catalogue,
        data=data,
        version=version,
        catalogue_key=f"catalogue/versions/{version.replace(':', '-')}.json",
        show_count=len(public_shows),
        episode_count=sum(len(season.episodes) for show in public_shows for season in show.seasons),
    )


def episodes_by_show_season(show: Show, episodes_by_season: dict[int, list[Episode]]) -> list[Episode]:
    return [episode for season in show.seasons for episode in episodes_by_season.get(season.id, [])]


def publish_catalogue(db: Session, storage: LocalStorage) -> BuiltCatalogue:
    built = build_catalogue(db, storage)
    storage.write_immutable(built.catalogue_key, built.data)
    storage.activate_pointer(built.catalogue_key)
    return built
