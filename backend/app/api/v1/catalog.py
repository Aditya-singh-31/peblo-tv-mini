from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import get_db, require_role
from app.models import PublishRun, User
from app.publishing.catalogue import CatalogueValidationError, publish_catalogue
from app.schemas.catalogue import (
    CatalogueSearchEpisode,
    CatalogueSearchItem,
    CatalogueSearchResponse,
    PublishedCatalogue,
)
from app.schemas.publishing import PublishResponse
from app.schemas.publish_history import PublishHistoryPage, PublishRunResponse
from app.storage.local import LocalStorage

router = APIRouter(prefix="/admin/catalog", tags=["admin-catalog"])
viewer_router = APIRouter(prefix="/catalog", tags=["catalog"])
catalogue_storage = LocalStorage()


def _empty_catalogue() -> PublishedCatalogue:
    return PublishedCatalogue(
        catalogue_version="empty",
        featured_hero=None,
        sections=[],
        categories=[],
        shows=[],
    )


def _load_live_catalogue() -> PublishedCatalogue:
    try:
        key = catalogue_storage.read_live_key()
        if key is None:
            return _empty_catalogue()
        return PublishedCatalogue.model_validate_json(catalogue_storage.read(key))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The published catalogue is temporarily unavailable.",
        ) from exc


@viewer_router.get("", response_model=PublishedCatalogue)
def get_catalog() -> PublishedCatalogue:
    return _load_live_catalogue()


@viewer_router.get("/search", response_model=CatalogueSearchResponse)
def search_catalog(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    language: str | None = Query(default=None),
    section: str | None = Query(default=None),
) -> CatalogueSearchResponse:
    catalogue = _load_live_catalogue()
    query = q.strip().casefold() if q else None
    category_filter = category.strip().casefold() if category else None
    language_filter = language.strip().casefold() if language else None
    section_filter = section.strip().casefold() if section else None

    section_show_ids = {
        show_id
        for item in catalogue.sections
        if not section_filter or item.key.casefold() == section_filter
        for show_id in item.show_ids
    }
    if section_filter and not section_show_ids:
        return CatalogueSearchResponse(items=[], total=0)

    items: list[CatalogueSearchItem] = []
    for show in catalogue.shows:
        if section_filter and show.id not in section_show_ids:
            continue
        if category_filter and not any(value.casefold() == category_filter for value in show.categories):
            continue

        candidate_episodes = [
            (season, episode)
            for season in show.seasons
            for episode in season.episodes
            if not language_filter
            or any(language.code.casefold() == language_filter for language in episode.languages)
        ]
        if language_filter and not candidate_episodes:
            continue

        show_matches = bool(
            query
            and (
                query in show.title.casefold()
                or any(query in value.casefold() for value in show.categories)
            )
        )
        episode_matches = [
            (season, episode)
            for season, episode in candidate_episodes
            if query and query in episode.title.casefold()
        ]
        if query and not show_matches and not episode_matches:
            continue

        selected_episodes = candidate_episodes if show_matches or not query else episode_matches
        selected_episodes.sort(key=lambda item: (item[0].number, item[1].title.casefold(), item[1].id))
        items.append(
            CatalogueSearchItem(
                show_id=show.id,
                title=show.title,
                synopsis=show.synopsis,
                categories=show.categories,
                poster=show.poster,
                banner=show.banner,
                thumbnail=show.thumbnail,
                episodes=[
                    CatalogueSearchEpisode(
                        id=episode.id,
                        title=episode.title,
                        synopsis=episode.synopsis,
                        duration_seconds=episode.duration_seconds,
                        thumbnail=episode.thumbnail,
                        languages=episode.languages,
                        season_number=season.number,
                        season_title=season.title,
                    )
                    for season, episode in selected_episodes
                ],
            )
        )

    items.sort(key=lambda item: (item.title.casefold(), item.show_id))
    return CatalogueSearchResponse(items=items, total=len(items))


def _start_run(db: Session, user: User) -> PublishRun:
    publish_run = PublishRun(
        initiated_by_id=user.id,
        status="running",
        outcome="running",
    )
    db.add(publish_run)
    db.commit()
    db.refresh(publish_run)
    return publish_run


def _finish_run(
    db: Session,
    publish_run: PublishRun,
    *,
    status_value: str,
    outcome: str,
    error_message: str | None = None,
    catalogue_version: str | None = None,
    catalogue_key: str | None = None,
    show_count: int = 0,
    episode_count: int = 0,
) -> None:
    publish_run.status = status_value
    publish_run.outcome = outcome
    publish_run.error_message = error_message
    publish_run.catalogue_version = catalogue_version
    publish_run.catalogue_key = catalogue_key
    publish_run.show_count = show_count
    publish_run.episode_count = episode_count
    publish_run.finished_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/publish", response_model=PublishResponse)
def publish(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> PublishResponse:
    publish_run = _start_run(db, current_user)
    try:
        built = publish_catalogue(db, catalogue_storage)
    except CatalogueValidationError as exc:
        _finish_run(
            db,
            publish_run,
            status_value="failed",
            outcome="validation_failed",
            error_message=exc.report.model_dump_json(),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "publish_run_id": publish_run.id,
                "outcome": "validation_failed",
                "validation_report": exc.report.model_dump(mode="json"),
            },
        ) from exc
    except Exception as exc:
        db.rollback()
        _finish_run(
            db,
            publish_run,
            status_value="failed",
            outcome="publish_failed",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "publish_run_id": publish_run.id,
                "outcome": "publish_failed",
                "message": "The catalogue was not activated.",
            },
        ) from exc

    _finish_run(
        db,
        publish_run,
        status_value="succeeded",
        outcome="published",
        catalogue_version=built.version,
        catalogue_key=built.catalogue_key,
        show_count=built.show_count,
        episode_count=built.episode_count,
    )
    return PublishResponse(
        publish_run_id=publish_run.id,
        outcome="published",
        catalogue_version=built.version,
        catalogue_key=built.catalogue_key,
        show_count=built.show_count,
        episode_count=built.episode_count,
    )


@router.get("/history", response_model=PublishHistoryPage)
def publish_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_role("editor", "admin")),
    db: Session = Depends(get_db),
) -> PublishHistoryPage:
    del current_user
    total = db.execute(select(func.count()).select_from(PublishRun)).scalar_one()
    runs = db.execute(
        select(PublishRun)
        .order_by(PublishRun.started_at.desc(), PublishRun.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return PublishHistoryPage(
        items=[PublishRunResponse.model_validate(run) for run in runs],
        total=total,
        page=page,
        page_size=page_size,
    )
